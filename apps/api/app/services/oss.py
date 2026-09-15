import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings

# 未配 OSS 时，原图落到 <api>/var/uploads/{object_key}，供 analyze_runner 回读上送 LLM。
_LOCAL_ROOT = Path(__file__).resolve().parents[2] / "var" / "uploads"


def is_oss_configured() -> bool:
    """是否已接入真实 OSS。由显式开关 settings.oss_enabled 决定（默认关）。

    ALLOW_MOCK 含 oss（或 APP_ENV=test）时一律当作未接入，原图改落本地
    var/uploads/——即「文件上传走 file 方式」，本地开发与跑测试都不碰真实 bucket。

    不能用 ali_access_key_id / oss_bucket 等推断：AK 与短信/内容审核共用，dev.env 里
    OSS bucket/role 又是占位假值——任一被填都会误判 OSS 为 true，使上传/分析走进
    未实现的 STS 分支。只有真正接入 OSS 时才在 prod 置 OSS_ENABLED=true。
    """
    if settings.is_mocked("oss"):
        return False
    return settings.oss_enabled


def _oss_ak() -> tuple[str, str]:
    """OSS 用 AK：优先 oss_access_key_id/secret，回退 ali_access_key_id/secret。"""
    return (
        settings.oss_access_key_id or settings.ali_access_key_id,
        settings.oss_access_key_secret or settings.ali_access_key_secret,
    )


def _norm_endpoint(ep: str) -> str:
    """补 scheme。oss2 需要带 http(s):// 的 endpoint；配置里常只写域名。"""
    ep = ep.strip()
    if ep and not ep.startswith(("http://", "https://")):
        ep = "https://" + ep
    return ep


def _internal_endpoint() -> str:
    """后端自身上传/回读走的 endpoint（同区 ECS 用内网，免公网流量费、更快）。"""
    return _norm_endpoint(settings.oss_endpoint or settings.oss_internal_endpoint)


def _public_endpoint() -> str:
    """给远端 LLM 签公网 GET URL 用的 endpoint。

    优先由 oss_public_base_url（bucket 虚拟主机域名）反推区域级 endpoint；否则把内网
    endpoint 里的 '-internal' 去掉得到公网 endpoint。
    """
    base = settings.oss_public_base_url.strip()
    if base:
        # https://<bucket>.oss-cn-beijing.aliyuncs.com -> https://oss-cn-beijing.aliyuncs.com
        host = base.split("://", 1)[-1]
        prefix = f"{settings.oss_bucket}."
        if host.startswith(prefix):
            host = host[len(prefix):]
        return "https://" + host.rstrip("/")
    ep = settings.oss_endpoint or settings.oss_internal_endpoint
    return _norm_endpoint(ep.replace("-internal", ""))


def _bucket(endpoint: str):
    """构造一个 oss2.Bucket（同步，仅本地签名/短时 PUT，无长连接）。"""
    import oss2

    ak_id, ak_secret = _oss_ak()
    return oss2.Bucket(oss2.Auth(ak_id, ak_secret), endpoint, settings.oss_bucket)


def put_oss_object(object_key: str, data: bytes, mime: str = "image/jpeg") -> None:
    """后端把原图字节写入 OSS（走内网 endpoint）。用于「后端代传」模式：只需 AK，无需 STS。

    注意这是同步阻塞调用（oss2 基于 requests）。analyze 的 2 分钟长任务不经此路径——它只
    用签名 URL 让 LLM 自己拉图；此处仅在上传瞬间跑一次，5MB 上行毫秒级，可接受。
    """
    _bucket(_internal_endpoint()).put_object(
        object_key, data, headers={"Content-Type": mime}
    )



def local_object_path(object_key: str) -> Path:
    """把 object_key 映射到本地存储路径，并防目录穿越。"""
    root = _LOCAL_ROOT.resolve()
    target = (root / object_key).resolve()
    if root not in target.parents and target != root:
        raise ValueError("invalid object_key")
    return target


def save_local_object(object_key: str, data: bytes) -> Path:
    """把上传字节写到本地（未配 OSS 时使用）。"""
    target = local_object_path(object_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def read_local_object(object_key: str) -> bytes:
    """回读本地原图字节（未配 OSS 时使用）。"""
    return local_object_path(object_key).read_bytes()


def generate_object_key(scope: str = "anon") -> str:
    """OSS object key: uploads/YYYY/MM/DD/{uuid}.jpg

    scope 暂未编进 key（保留扩展位）；如需按用户分隔可改为 uploads/{scope}/...
    """
    today = datetime.utcnow()
    return f"uploads/{today.year:04d}/{today.month:02d}/{today.day:02d}/{uuid.uuid4()}.jpg"


@dataclass
class StsCredentials:
    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration_iso: str


def _sts_endpoint() -> str:
    """STS 服务接入点。优先用显式配置，否则按区域拼 sts.<region>.aliyuncs.com。"""
    if settings.oss_sts_endpoint:
        return settings.oss_sts_endpoint
    region = settings.ali_region or "cn-hangzhou"
    return f"sts.{region}.aliyuncs.com"


def _upload_policy(object_key: str) -> str:
    """最小权限 policy：只允许 PutObject 到这一个 object_key，防越权覆盖他人图片。"""
    import json

    resource = f"acs:oss:*:*:{settings.oss_bucket}/{object_key}"
    return json.dumps(
        {
            "Version": "1",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["oss:PutObject"],
                    "Resource": [resource],
                }
            ],
        }
    )


async def issue_sts_for_upload(object_key: str) -> StsCredentials:
    """
    未配 OSS（本地联调）：返回固定假凭证，前端改走 /api/upload/local 落盘。
    已配 OSS 但没填 STS role（后端代传模式）：同样返回假凭证，前端走 /api/upload/local，
                    由后端用主 AK 代传 OSS（见 upload_local）。
    已配 OSS 且填了 STS role：STS AssumeRole 换一组临时凭证，policy 限定只能 PutObject 到本
                    object_key，前端用它直传 OSS，原图字节不经过后端内存。
    """
    if not is_oss_configured() or not settings.oss_sts_role_arn:
        return StsCredentials(
            access_key_id="STS.MOCK_ID",
            access_key_secret="MOCK_SECRET",
            security_token="MOCK_TOKEN",
            expiration_iso=(
                datetime.utcnow() + timedelta(seconds=settings.oss_sts_ttl)
            ).isoformat()
            + "Z",
        )

    # 延迟导入，避免本地无 OSS 场景也强加载 STS SDK
    from alibabacloud_sts20150401 import models as sts_models
    from alibabacloud_sts20150401.client import Client as StsClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models

    config = open_api_models.Config(
        access_key_id=settings.ali_access_key_id,
        access_key_secret=settings.ali_access_key_secret,
        endpoint=_sts_endpoint(),
    )
    client = StsClient(config)
    # STS 要求 DurationSeconds ≥ 900（15 分钟），oss_sts_ttl 若更小则抬到下限
    duration = max(900, settings.oss_sts_ttl)
    req = sts_models.AssumeRoleRequest(
        role_arn=settings.oss_sts_role_arn,
        role_session_name="venus-upload",
        policy=_upload_policy(object_key),
        duration_seconds=duration,
    )
    resp = await client.assume_role_with_options_async(req, util_models.RuntimeOptions())
    cred = resp.body.credentials
    return StsCredentials(
        access_key_id=cred.access_key_id,
        access_key_secret=cred.access_key_secret,
        security_token=cred.security_token,
        expiration_iso=cred.expiration,
    )


def signed_download_url(object_key: str, ttl_seconds: int | None = None) -> str:
    """供 LLM 服务从 OSS 拉图的签名 GET URL。

    未配 OSS：返回 mock URL（本地不会真去 OSS 拉）。
    已配 OSS：用主账号 AK 对指定 object_key 签一个有时效的 GET URL。LLM 多为公网直连，
             故用公网 endpoint 签名；有效期取 settings.oss_download_url_ttl（外置 .env 可调）。
    """
    ttl_seconds = ttl_seconds or settings.oss_download_url_ttl
    if not is_oss_configured():
        endpoint = settings.oss_internal_endpoint or "http://mock-oss"
        return f"{endpoint}/{object_key}?mock=1"

    # 用公网 endpoint 签名：内网 oss_endpoint 只在 VPC 内可达，远端 LLM 拉不到。
    # slash_safe=True：object_key 里的 '/' 不转义，保持 uploads/YYYY/MM/DD/xxx.jpg 结构
    return _bucket(_public_endpoint()).sign_url(
        "GET", object_key, ttl_seconds, slash_safe=True
    )
