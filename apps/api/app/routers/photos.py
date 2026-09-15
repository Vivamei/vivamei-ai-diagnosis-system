from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select

from app.core.config import settings
from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.models.photo import ModerationStatus, Photo
from app.schemas.upload import PhotoRegisterRequest, PhotoRegisterResponse
from app.services.moderation import scan_image

router = APIRouter(prefix="/api/photos", tags=["photos"])


async def _moderate_in_bg(photo_id: int) -> None:
    """后台任务：拉 OSS object 跑内容安全，更新 photo.moderation_status。"""
    from app.db.session import SessionLocal

    async with SessionLocal() as s:
        p = (
            await s.execute(select(Photo).where(Photo.id == photo_id))
        ).scalar_one()
        result = await scan_image(p.oss_key)
        p.moderation_status = (
            ModerationStatus.passed if result.passed else ModerationStatus.rejected
        )
        p.moderation_raw = result.raw
        await s.commit()


@router.post("", response_model=PhotoRegisterResponse)
async def register_photo(
    req: PhotoRegisterRequest,
    bg: BackgroundTasks,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    p = Photo(
        user_id=user.id,
        oss_key=req.ossKey,
        width=req.width,
        height=req.height,
        bytes=req.bytes,
        mime=req.mime,
        client_ip=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=settings.photo_ttl_days),
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    bg.add_task(_moderate_in_bg, p.id)
    return PhotoRegisterResponse(photoId=p.id, moderationStatus=p.moderation_status.value)
