"""
services/image.py

Image processing service.
Handles upload, validation, and OSS URL generation.
"""

import io
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from PIL import Image
import oss2
import requests
from core.config import Settings
from core.exceptions import ImageQualityError, ConfigurationError

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ImageService:
    """Handles image upload, validation, and OSS URL generation."""

    def __init__(self, settings: Settings):
        self.settings = settings

        # 校验 OSS 配置是否完整
        if not all([
            settings.OSS_ACCESS_KEY_ID.strip(),
            settings.OSS_ACCESS_KEY_SECRET.strip(),
            settings.OSS_ENDPOINT.strip(),
            settings.OSS_BUCKET_NAME.strip()
        ]):
            raise ConfigurationError(
                "OSS 配置不完整，请检查 .env 文件中的 OSS_ACCESS_KEY_ID, "
                "OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, OSS_BUCKET_NAME"
            )

        # 初始化 OSS 客户端
        auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        self.bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)

    def save_upload(self, file: UploadFile) -> str:
        """
        Save uploaded file to OSS and return its public URL.
        注意：这里返回的是可以直接被大模型访问的公网 URL 字符串。
        """
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ImageQualityError(
                message="仅支持 jpg、jpeg、png、webp 格式图片。",
                details={"filename": file.filename},
            )

        # 生成唯一文件名，按日期或目录分类更佳，这里简单放在 uploads 下
        filename = f"uploads/{uuid.uuid4().hex}{suffix}"

        # 直接将内存中的文件流上传到 OSS，避免落盘占用本地空间
        self.bucket.put_object(filename, file.file)

        # 拼接并返回 OSS 公网 URL
        # 注意：如果你的 endpoint 包含 http 前缀，需要做一下清洗
        endpoint_clean = self.settings.OSS_ENDPOINT.replace('http://', '').replace('https://', '')
        public_url = f"https://{self.settings.OSS_BUCKET_NAME}.{endpoint_clean}/{filename}"

        return public_url

    def validate_quality(self, image_url: str) -> dict[str, Any]:
        """
        Basic image quality check.
        通过 HTTP 请求下载图片到内存，再进行校验。
        """
        try:
            # 1. 发起 HTTP GET 请求，获取图片的二进制数据
            # 注意：这里需要确保你的服务器能访问公网
            response = requests.get(image_url, timeout=5)
            response.raise_for_status()  # 如果 HTTP 状态码不是 200，则抛出异常

            # 2. 将二进制数据包装成一个 BytesIO 对象（一个内存中的文件类对象）
            image_bytes = io.BytesIO(response.content)

            # 3. 将内存对象交给 PIL 打开和处理
            with Image.open(image_bytes) as img:
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
        except requests.exceptions.RequestException as exc:
            # 专门处理网络请求相关的错误
            raise ImageQualityError(
                message=f"图片下载失败，请检查网络或重新上传。错误信息：{str(exc)}",
            )
        except Exception as exc:
            # 处理其他错误，比如图片格式损坏等
            raise ImageQualityError(
                message=f"图片读取失败，请重新上传。错误信息：{str(exc)}",
            )

    def build_public_url(self, oss_url: str) -> str:
        """
        直接返回 OSS 公网 URL。
        由于 save_upload 已经返回了完整 URL，此方法仅作兼容或透传使用。
        """
        return oss_url