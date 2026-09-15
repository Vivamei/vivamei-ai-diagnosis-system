"""微信小程序开放接口封装：code2session 换 openid、phoneCode 换手机号。

未配置 wx_appid/wx_secret 时进入 mock 模式：openid 由 js_code 派生（同 code 稳定），
手机号返回 sms_test_phone_prefix 打头的固定号。这样小程序端在拿到正式 appid 之前
（project.config.json 仍是 touristappid）也能跑通完整登录链路，与短信的测试模式一致。
"""

import hashlib

import httpx
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppError

_API = "https://api.weixin.qq.com"
# 微信 access_token 官方有效期 7200s，提前 200s 过期以避开边界。
_TOKEN_CACHE_TTL = 7000
_TOKEN_CACHE_KEY = "wx:access_token"


def is_wx_configured() -> bool:
    """是否接真实微信开放接口。ALLOW_MOCK 含 wechat（或 APP_ENV=test）时一律当作未配。"""
    if settings.is_mocked("wechat"):
        return False
    return bool(settings.wx_appid and settings.wx_secret)


def _mock_openid(js_code: str) -> str:
    return "mock_" + hashlib.sha256(js_code.encode()).hexdigest()[:24]


def _mock_phone(openid: str) -> str:
    # 用 openid 派生 8 位后缀，保证同一 mock 用户每次拿到同一号码
    digits = str(int(hashlib.sha256(openid.encode()).hexdigest()[:10], 16))
    return settings.sms_test_phone_prefix + digits.rjust(8, "0")[:8]


async def _get(client: httpx.AsyncClient, path: str, **params) -> dict:
    resp = await client.get(f"{_API}{path}", params=params)
    resp.raise_for_status()
    return resp.json()


async def code2session(js_code: str) -> dict:
    """wx.login 的 code 换 openid/unionid。返回 {"openid":..., "unionid":...|None}"""
    if not is_wx_configured():
        logger.warning("[wx] 未配置 appid/secret，code2session 走 mock")
        return {"openid": _mock_openid(js_code), "unionid": None}

    async with httpx.AsyncClient(timeout=10) as client:
        data = await _get(
            client,
            "/sns/jscode2session",
            appid=settings.wx_appid,
            secret=settings.wx_secret,
            js_code=js_code,
            grant_type="authorization_code",
        )
    if data.get("errcode"):
        logger.warning("[wx] code2session 失败 {}", data)
        raise AppError("WX_CODE_INVALID", "登录凭证无效，请重试", status_code=400)
    return {"openid": data["openid"], "unionid": data.get("unionid")}


async def _access_token(r) -> str:
    cached = await r.get(_TOKEN_CACHE_KEY)
    if cached:
        return cached.decode() if isinstance(cached, bytes) else cached

    async with httpx.AsyncClient(timeout=10) as client:
        data = await _get(
            client,
            "/cgi-bin/token",
            grant_type="client_credential",
            appid=settings.wx_appid,
            secret=settings.wx_secret,
        )
    token = data.get("access_token")
    if not token:
        logger.warning("[wx] 获取 access_token 失败 {}", data)
        raise AppError("WX_UPSTREAM_ERROR", "快捷登录服务暂不可用", status_code=502)
    await r.setex(_TOKEN_CACHE_KEY, _TOKEN_CACHE_TTL, token)
    return token


async def get_phone_number(phone_code: str, openid: str, r) -> str:
    """<button open-type="getPhoneNumber"> 回调里的 code 换真实手机号（纯号码，不带区号）。"""
    if not is_wx_configured():
        logger.warning("[wx] 未配置 appid/secret，getPhoneNumber 走 mock")
        return _mock_phone(openid)

    token = await _access_token(r)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{_API}/wxa/business/getuserphonenumber",
            params={"access_token": token},
            json={"code": phone_code},
        )
        resp.raise_for_status()
        data = resp.json()
    if data.get("errcode"):
        logger.warning("[wx] getPhoneNumber 失败 {}", data)
        # 40001 = access_token 失效（如后台改过 secret），清缓存让下次重取
        if data.get("errcode") == 40001:
            await r.delete(_TOKEN_CACHE_KEY)
        raise AppError("WX_PHONE_FAILED", "手机号授权失败，请重试", status_code=400)
    phone = (data.get("phone_info") or {}).get("purePhoneNumber")
    if not phone:
        raise AppError("WX_PHONE_FAILED", "未获取到手机号", status_code=400)
    return phone
