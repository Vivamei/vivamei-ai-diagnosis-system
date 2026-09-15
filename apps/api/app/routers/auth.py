import secrets
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from jose import JWTError
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import (
    decode_token,
    issue_access_token,
    issue_refresh_token,
    issue_wx_bind_token,
)
from app.deps.db import get_db
from app.deps.redis import get_redis
from app.models.user import User
from app.schemas.auth import (
    AccessResponse,
    LogoutRequest,
    RefreshRequest,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
    TokenPair,
    UserBrief,
    WxLoginRequest,
    WxLoginResponse,
    WxPhoneRequest,
)
from app.services.phone_crypto import encrypt_phone, hash_phone
from app.services.ratelimit import RateLimiter
from app.services.sms import get_sms_provider, is_sms_configured
from app.services.wechat import code2session, get_phone_number

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/sms/send", response_model=SmsSendResponse)
async def sms_send(req: SmsSendRequest, request: Request, r=Depends(get_redis)):
    ph = hash_phone(req.phone)
    ip = request.client.host if request.client else "unknown"

    # 1) 同手机号 60s 内不能重复发
    if await r.exists(f"sms:send:{ph}"):
        raise AppError("AUTH_SMS_TOO_FREQUENT", "60 秒内只能请求一次", status_code=429)

    # 2) 同 IP 每分钟限 N 次
    ip_rl = RateLimiter(r, f"rl:ip:sms:{ip}", settings.rl_sms_ip_per_min, 60)
    if not await ip_rl.allow():
        raise AppError("AUTH_SMS_TOO_FREQUENT", "IP 频率过高", status_code=429)

    # 3) 同手机号每天限 N 次
    day_rl = RateLimiter(r, f"rl:sms:day:{ph}", settings.rl_sms_phone_per_day, 86400)
    if not await day_rl.allow():
        raise AppError("AUTH_SMS_TOO_FREQUENT", "今日发送次数过多", status_code=429)

    if is_sms_configured():
        code = f"{secrets.randbelow(1_000_000):06d}"
    else:
        # 测试模式（未配短信模板）：仅测试手机号可收到固定验证码，其他号码拒绝。
        if not req.phone.startswith(settings.sms_test_phone_prefix):
            raise AppError(
                "AUTH_SMS_NOT_AVAILABLE", "短信服务未开通", status_code=403
            )
        code = settings.sms_test_code
    await r.setex(f"sms:code:{ph}", 300, code)
    await r.setex(f"sms:send:{ph}", 60, "1")
    await get_sms_provider().send_code(req.phone, code)
    return SmsSendResponse()


@router.post("/sms/verify", response_model=TokenPair)
async def sms_verify(req: SmsVerifyRequest, r=Depends(get_redis), db=Depends(get_db)):
    ph = hash_phone(req.phone)
    saved = await r.get(f"sms:code:{ph}")
    if not saved or saved.decode() != req.code:
        raise AppError("AUTH_SMS_INVALID", "验证码无效或已过期", status_code=400)
    await r.delete(f"sms:code:{ph}")

    user = (
        await db.execute(select(User).where(User.phone_hash == ph))
    ).scalar_one_or_none()
    if not user:
        user = User(
            phone=encrypt_phone(req.phone),
            phone_hash=ph,
            nickname=req.username,
            consent_at=datetime.utcnow(),
            consent_ver=req.consentVer,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif req.username and not user.nickname:
        # 老用户第一次带上 username 时补写
        user.nickname = req.username
        await db.commit()
        await db.refresh(user)

    return TokenPair(
        accessToken=issue_access_token(user.id),
        refreshToken=issue_refresh_token(user.id),
        expiresIn=settings.jwt_access_ttl_seconds,
        user=UserBrief(id=user.id, nickname=user.nickname),
    )


@router.post("/refresh", response_model=AccessResponse)
async def refresh(req: RefreshRequest, r=Depends(get_redis)):
    try:
        claims = decode_token(req.refreshToken)
    except JWTError:
        raise AppError("AUTH_INVALID_TOKEN", "invalid refresh", status_code=401)
    if claims.get("type") != "refresh":
        raise AppError("AUTH_INVALID_TOKEN", "wrong type", status_code=401)
    if await r.exists(f"jwt:blacklist:{req.refreshToken}"):
        raise AppError("AUTH_INVALID_TOKEN", "refresh revoked", status_code=401)
    uid = int(claims["sub"])
    return AccessResponse(
        accessToken=issue_access_token(uid),
        expiresIn=settings.jwt_access_ttl_seconds,
    )


@router.post("/logout", status_code=204)
async def logout(req: LogoutRequest, r=Depends(get_redis)):
    try:
        claims = decode_token(req.refreshToken)
    except JWTError:
        # 已无效，幂等成功
        return
    exp = int(claims.get("exp", 0))
    ttl = max(exp - int(time.time()), 1)
    await r.setex(f"jwt:blacklist:{req.refreshToken}", ttl, "1")


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        accessToken=issue_access_token(user.id),
        refreshToken=issue_refresh_token(user.id),
        expiresIn=settings.jwt_access_ttl_seconds,
        user=UserBrief(id=user.id, nickname=user.nickname),
    )


@router.post("/wx/login", response_model=WxLoginResponse)
async def wx_login(req: WxLoginRequest, db=Depends(get_db)):
    """小程序静默登录：openid 已绑过用户就直接发 token，否则要手机号。"""
    sess = await code2session(req.code)
    openid = sess["openid"]

    user = (
        await db.execute(select(User).where(User.wx_openid == openid))
    ).scalar_one_or_none()
    if user:
        return WxLoginResponse(needPhone=False, tokens=_token_pair(user))

    return WxLoginResponse(
        needPhone=True,
        bindToken=issue_wx_bind_token(openid, sess.get("unionid")),
    )


@router.post("/wx/phone", response_model=TokenPair)
async def wx_phone(req: WxPhoneRequest, r=Depends(get_redis), db=Depends(get_db)):
    """手机号授权回调：openid 从 bindToken 取（不信客户端自报），换到手机号后建号或绑号。"""
    try:
        claims = decode_token(req.bindToken)
    except JWTError:
        raise AppError("AUTH_INVALID_TOKEN", "登录已过期，请重试", status_code=401)
    if claims.get("type") != "wxbind":
        raise AppError("AUTH_INVALID_TOKEN", "wrong type", status_code=401)
    openid = claims["openid"]
    unionid = claims.get("unionid")

    phone = await get_phone_number(req.phoneCode, openid, r)
    ph = hash_phone(phone)

    user = (
        await db.execute(select(User).where(User.phone_hash == ph))
    ).scalar_one_or_none()
    if user:
        # 短信注册的老用户首次用微信进来：把 openid 补绑到既有账号，不再开新号
        user.wx_openid = openid
        user.wx_unionid = unionid
        if req.username and not user.nickname:
            user.nickname = req.username
    else:
        user = User(
            phone=encrypt_phone(phone),
            phone_hash=ph,
            nickname=req.username,
            wx_openid=openid,
            wx_unionid=unionid,
            consent_at=datetime.utcnow(),
            consent_ver=req.consentVer,
        )
        db.add(user)
    await db.commit()
    await db.refresh(user)

    return _token_pair(user)
