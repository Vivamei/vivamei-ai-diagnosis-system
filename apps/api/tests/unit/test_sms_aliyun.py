"""AliyunSmsProvider 单测：mock 掉 SDK，验证三条路径与错误映射。"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.exceptions import AppError


@pytest.fixture
def _aliyun_env(monkeypatch):
    monkeypatch.setattr(settings, "ali_access_key_id", "LTAI5_TEST")
    monkeypatch.setattr(settings, "ali_access_key_secret", "SECRET_TEST")
    monkeypatch.setattr(settings, "ali_sms_sign", "测试签名")
    monkeypatch.setattr(settings, "ali_sms_template_login", "SMS_TEST_001")


def _make_provider():
    # 推迟 import 到 fixture 设置环境变量之后
    from app.services.sms.aliyun import AliyunSmsProvider

    return AliyunSmsProvider()


def test_init_rejects_missing_creds(monkeypatch):
    monkeypatch.setattr(settings, "ali_access_key_id", "")
    from app.services.sms.aliyun import AliyunSmsProvider

    with pytest.raises(RuntimeError, match="ACCESS_KEY"):
        AliyunSmsProvider()


def test_init_rejects_missing_sign(monkeypatch):
    monkeypatch.setattr(settings, "ali_access_key_id", "x")
    monkeypatch.setattr(settings, "ali_access_key_secret", "y")
    monkeypatch.setattr(settings, "ali_sms_sign", "")
    from app.services.sms.aliyun import AliyunSmsProvider

    with pytest.raises(RuntimeError, match="SIGN"):
        AliyunSmsProvider()


@pytest.mark.asyncio
async def test_send_code_ok(_aliyun_env):
    p = _make_provider()
    fake_resp = SimpleNamespace(
        body=SimpleNamespace(
            code="OK", message="OK", biz_id="biz_abc", request_id="req_xyz"
        )
    )

    async def fake_send(req):
        # 顺便校验 request 字段拼装正确
        assert req.phone_numbers == "13800138000"
        assert req.sign_name == "测试签名"
        assert req.template_code == "SMS_TEST_001"
        assert '"code": "654321"' in req.template_param
        return fake_resp

    with patch.object(p._client, "send_sms_async", side_effect=fake_send):
        await p.send_code("13800138000", "654321")  # 不抛即成功


@pytest.mark.asyncio
async def test_send_code_business_fail_raises_app_error(_aliyun_env):
    p = _make_provider()
    fake_resp = SimpleNamespace(
        body=SimpleNamespace(
            code="isv.BUSINESS_LIMIT_CONTROL",
            message="触发频控",
            biz_id=None,
            request_id="req_1",
        )
    )

    async def fake_send(req):
        return fake_resp

    with patch.object(p._client, "send_sms_async", side_effect=fake_send):
        with pytest.raises(AppError) as ei:
            await p.send_code("13800138000", "123456")
    assert ei.value.code == "AUTH_SMS_SEND_FAILED"
    assert ei.value.status_code == 502
    assert ei.value.retryable is True


@pytest.mark.asyncio
async def test_send_code_sdk_exception_raises_app_error(_aliyun_env):
    p = _make_provider()

    async def boom(req):
        raise ConnectionError("network down")

    with patch.object(p._client, "send_sms_async", side_effect=boom):
        with pytest.raises(AppError) as ei:
            await p.send_code("13800138000", "123456")
    assert ei.value.code == "AUTH_SMS_SEND_FAILED"
    assert ei.value.retryable is True
