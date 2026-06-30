"""
services/image.py

Image processing service.
Handles upload, validation, and URL generation.
"""

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from PIL import Image

from core.config import Settings
from core.exceptions import ImageQualityError, ConfigurationError

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ImageService:
    """Handles image upload, validation, and URL generation."""

    def __init__(self, settings: Settings, upload_dir: Path | None = None):
        self.settings = settings
        self.upload_dir = upload_dir or (Path(__file__).resolve().parent.parent / "uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file: UploadFile) -> Path:
        """Save uploaded file and return its path."""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ImageQualityError(
                message="仅支持 jpg、jpeg、png、webp 格式图片。",
                details={"filename": file.filename},
            )

        filename = f"{uuid.uuid4().hex}{suffix}"
        save_path = self.upload_dir / filename

        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return save_path

    def validate_quality(self, image_path: Path) -> dict[str, Any]:
        """Basic image quality check."""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                passed = True
                problems: list[str] = []

                if width < 300 or height < 300:
                    passed = False
                    problems.append("图片分辨率过低，建议上传更清晰的正面照。")

                ratio = width / height
                if ratio < 0.4 or ratio > 2.5:
                    problems.append("图片比例较异常，建议上传单人正面头像或半身照。")

                return {
                    "passed": passed,
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "problems": problems,
                }
        except Exception as exc:
            raise ImageQualityError(
                message=f"图片读取失败，请重新上传。错误信息：{str(exc)}",
            )

    def build_public_url(self, image_path: Path) -> str:
        """Convert local image path to public URL."""
        if self.settings.is_mock:
            return f"local://{image_path.name}"

        if not self.settings.public_base_url:
            raise ConfigurationError(
                "真实调用视觉大模型时需要配置 PUBLIC_BASE_URL。"
                "如果只是本地测试，请设置 LLM_PROVIDER=mock。",
            )

        return f"{self.settings.public_base_url}/uploads/{image_path.name}"
