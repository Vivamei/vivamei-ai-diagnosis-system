"""阿里云短信 Provider（生产用）。

只在 APP_ENV=prod 时由 services/sms/__init__.py 实例化。
依赖：alibabacloud-dysmsapi20170525 (^3.0)，已在 pyproject.toml 声明。

调用前提（运营/甲方完成）：
  1) 阿里云控制台开通短信服务
  2) 申请并通过签名（ALI_SMS_SIGN）
  3) 申请并通过验证码模板（ALI_SMS_TEMPLATE_LOGIN），模板含 ${code} 变量
  4) RAM 子账号 AK/SK（最小权限 dysmsapi:SendSms）

返回失败时一律抛 AUTH_SMS_SEND_FAILED，让前端兜底"稍后重试"，
具体业务码（签名未审 / 频控 / 余额不足）只进日志，不暴露给用户。
"""
import json

from alibabacloud_dysmsapi20170525 import models as dysms_models
from alibabacloud_dysmsapi20170525.client import Client as DysmsClient
from alibabacloud_tea_openapi import models as open_api_models
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppError
from app.services.sms.base import SmsProvider


def _mask(phone: str) -> str:
    return phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else "***"


class AliyunSmsProvider(SmsProvider):
    name = "aliyun"

    def __init__(self) -> None:
        if not (settings.ali_access_key_id and settings.ali_access_key_secret):
            raise RuntimeError(
                "AliyunSmsProvider requires ALI_ACCESS_KEY_ID / ALI_ACCESS_KEY_SECRET"
            )
        if not (settings.ali_sms_sign and settings.ali_sms_template_login):
            raise RuntimeError(
                "AliyunSmsProvider requires ALI_SMS_SIGN / ALI_SMS_TEMPLATE_LOGIN"
            )
        # 短信服务走中心化 endpoint，不分 region
        config = open_api_models.Config(
            access_key_id=settings.ali_access_key_id,
            access_key_secret=settings.ali_access_key_secret,
            endpoint="dysmsapi.aliyuncs.com",
        )
        self._client = DysmsClient(config)

    async def send_code(self, phone: str, code: str) -> None:
        req = dysms_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=settings.ali_sms_sign,
            template_code=settings.ali_sms_template_login,
            template_param=json.dumps({"code": code}, ensure_ascii=False),
        )
        masked = _mask(phone)
        try:
            resp = await self._client.send_sms_async(req)
        except Exception as e:  # 网络 / 鉴权 / SDK 异常
            logger.bind(phone=masked).exception("[Aliyun SMS] sdk error: {}", e)
            raise AppError(
                "AUTH_SMS_SEND_FAILED",
                "短信发送失败，请稍后重试",
                status_code=502,
                retryable=True,
            )

        body = resp.body
        # body.code 为 "OK" 才算业务成功；其他码均视为发送失败
        # 常见错误码（仅举几例，全集见阿里云短信 API 文档）：
        #   isv.BUSINESS_LIMIT_CONTROL    频控（同号 1min/1h/1day 上限）
        #   isv.SMS_SIGNATURE_ILLEGAL     签名未审核 / 不存在
        #   isv.SMS_TEMPLATE_ILLEGAL      模板未审核 / 不存在
        #   isv.AMOUNT_NOT_ENOUGH         账户余额不足
        #   isv.MOBILE_NUMBER_ILLEGAL     手机号格式不合法
        if body.code != "OK":
            logger.bind(phone=masked).error(
                "[Aliyun SMS] business fail code={} message={} biz_id={} request_id={}",
                body.code,
                body.message,
                body.biz_id,
                body.request_id,
            )
            raise AppError(
                "AUTH_SMS_SEND_FAILED",
                "短信发送失败，请稍后重试",
                status_code=502,
                retryable=True,
            )

        logger.bind(phone=masked).info(
            "[Aliyun SMS] ok biz_id={} request_id={}", body.biz_id, body.request_id
        )
