from dataclasses import dataclass

from app.core.config import settings


@dataclass
class ScanResult:
    passed: bool
    raw: dict


async def scan_image_mock(object_key: str) -> ScanResult:
    """Mock 图片机审：object_key 含 'REJECT' 视为不通过。"""
    if "REJECT" in object_key:
        return ScanResult(False, {"label": "violation", "scene": "porn"})
    return ScanResult(True, {"label": "pass"})


async def scan_text_mock(text: str) -> ScanResult:
    """Mock 文本机审：内置一个极小关键字集合。生产用阿里云内容安全 textScan。"""
    bad = ["保证治愈", "100%", "最佳", "根治", "立竿见影"]
    hits = [w for w in bad if w in text]
    return ScanResult(not hits, {"hits": hits})


def is_moderation_configured() -> bool:
    """是否接真实内容安全（阿里云 Green）。

    用显式开关 moderation_enabled，不能靠 ali_access_key_id 推断：AK 与短信共用，
    填了短信会误判审核为真、走进未实现分支使照片卡在 pending。
    ALLOW_MOCK 含 moderation（或 APP_ENV=test）时一律当作未接入。
    """
    if settings.is_mocked("moderation"):
        return False
    return settings.moderation_enabled


async def scan_image(object_key: str) -> ScanResult:
    if not is_moderation_configured():
        return await scan_image_mock(object_key)
    # TODO(prod): 调 alibabacloud-green imageScan
    raise NotImplementedError("Aliyun Green imageScan to implement before prod")


async def scan_text(text: str) -> ScanResult:
    if not is_moderation_configured():
        return await scan_text_mock(text)
    # TODO(prod): 调 alibabacloud-green textScan
    raise NotImplementedError("Aliyun Green textScan to implement before prod")
