from fastapi import APIRouter, Depends, File, Form, UploadFile
from loguru import logger
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import AppError
from app.deps.auth import CurrentUser, get_current_user
from app.schemas.upload import UploadTokenResponse
from app.services.oss import (
    generate_object_key,
    is_oss_configured,
    issue_sts_for_upload,
    put_oss_object,
    save_local_object,
)

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/token", response_model=UploadTokenResponse)
async def get_upload_token(user: CurrentUser = Depends(get_current_user)):
    key = generate_object_key(scope=f"user{user.id}")
    sts = await issue_sts_for_upload(key)
    return UploadTokenResponse(
        ossEndpoint=settings.oss_endpoint or "http://mock-oss",
        accessKeyId=sts.access_key_id,
        accessKeySecret=sts.access_key_secret,
        securityToken=sts.security_token,
        expiration=sts.expiration_iso,
        objectKey=key,
        maxBytes=settings.photo_max_bytes,
    )


@router.post("/local")
async def upload_local(
    objectKey: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """原图直传落地。
    未配 OSS：落到 <api>/var/uploads/{objectKey}，分析时回读上送 LLM。
    已配 OSS 但走后端代传（没填 STS role）：后端用主 AK 把字节 PUT 进 OSS（走内网 endpoint），
        分析时给 LLM 签公网 GET URL 拉图，字节不在内存里驻留 2 分钟。"""
    data = await file.read()
    if len(data) > settings.photo_max_bytes:
        raise AppError(
            "PHOTO_TOO_LARGE",
            f"图片超过上限 {settings.photo_max_bytes} bytes",
            status_code=413,
        )
    if is_oss_configured():
        await run_in_threadpool(
            put_oss_object, objectKey, data, file.content_type or "image/jpeg"
        )
    else:
        await run_in_threadpool(save_local_object, objectKey, data)
    logger.info(
        "[upload local] user={} objectKey={} bytes={} mime={} oss={}",
        user.id,
        objectKey,
        len(data),
        file.content_type,
        is_oss_configured(),
    )
    return {"objectKey": objectKey, "bytes": len(data)}
