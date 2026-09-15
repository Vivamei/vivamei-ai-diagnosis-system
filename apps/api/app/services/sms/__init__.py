from app.core.config import settings
from app.services.sms.base import SmsProvider
from app.services.sms.mock import MockSmsProvider

_provider: SmsProvider | None = None


def is_sms_configured() -> bool:
    """是否已开通真实短信服务。四项（AK id/secret、签名、模板）全齐才算配置。

    ALLOW_MOCK 含 sms（或 APP_ENV=test）时一律当作未配置，即使凭据齐也不会真发短信、
    不会真扣额度——跑测试时这是防止误发的最后一道闸。

    未配置时走测试模式：MockSmsProvider 打印验证码，仅测试手机号可用固定码。
    """
    if settings.is_mocked("sms"):
        return False
    return bool(
        settings.ali_access_key_id
        and settings.ali_access_key_secret
        and settings.ali_sms_sign
        and settings.ali_sms_template_login
    )


def get_sms_provider() -> SmsProvider:
    """单例 Provider。配了短信模板 → Aliyun，否则 → Mock（测试模式）。

    AliyunSmsProvider 依赖阿里云 SDK，仅正式短信需要，故延迟 import，
    未配置时无该依赖也能跑。
    """
    global _provider
    if _provider is None:
        if is_sms_configured():
            from app.services.sms.aliyun import AliyunSmsProvider

            _provider = AliyunSmsProvider()
        else:
            _provider = MockSmsProvider()
    return _provider
