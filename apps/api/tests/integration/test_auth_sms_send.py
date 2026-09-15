import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.deps.redis import get_redis
from app.main import app
from app.services.phone_crypto import hash_phone
from app.services.sms import get_sms_provider


def _test_phone(suffix: str) -> str:
    """造一个 mock 短信认的手机号。

    mock 模式只放行 SMS_TEST_PHONE_PREFIX（默认 133）开头的号，其余一律 403。
    跟着配置拼而不是写死 138，改了前缀测试也不用动。
    """
    return (settings.sms_test_phone_prefix + suffix).ljust(11, "0")[:11]


_HAPPY_PHONE = _test_phone("00001111")
_THROTTLE_PHONE = _test_phone("00002222")
# 非测试号段，用来验证 mock 模式的拒绝分支。
_REJECT_PHONE = "13800138000"


@pytest.fixture(autouse=True)
async def _reset_sms_limits():
    """清掉上一轮留下的频控键。

    发送间隔键 60s、IP 每分钟 5 次的计数器都在 redis 里，60 秒内重跑测试会被
    自己上一轮的记录挡成 429，看起来像随机失败。被拒的号也要清：日限计数（10 次/天，
    TTL 一天）在号段校验之前就自增了，攒够 10 次后拒绝分支会先返回 429 而不是 403。
    """
    async for r in get_redis():
        keys = list(await r.keys("rl:ip:sms:*"))
        for phone in (_HAPPY_PHONE, _THROTTLE_PHONE, _REJECT_PHONE):
            ph = hash_phone(phone)
            keys += [f"sms:code:{ph}", f"sms:send:{ph}", f"rl:sms:day:{ph}"]
        if keys:
            await r.delete(*keys)
        break
    yield


@pytest.mark.asyncio
async def test_sms_send_happy_path():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/auth/sms/send",
            json={"phone": _HAPPY_PHONE, "scene": "login"},
        )
    assert r.status_code == 200
    assert r.json()["expiresIn"] == 300
    p = get_sms_provider()
    assert p.last_sent[0] == _HAPPY_PHONE
    assert len(p.last_sent[1]) == 6


@pytest.mark.asyncio
async def test_sms_send_rejects_non_test_phone():
    """mock 模式下非测试号段必须被拒，免得误以为真能发短信。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/auth/sms/send",
            json={"phone": _REJECT_PHONE, "scene": "login"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "AUTH_SMS_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_sms_send_throttled_60s():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        await ac.post(
            "/api/auth/sms/send",
            json={"phone": _THROTTLE_PHONE, "scene": "login"},
        )
        r = await ac.post(
            "/api/auth/sms/send",
            json={"phone": _THROTTLE_PHONE, "scene": "login"},
        )
    assert r.status_code == 429
    assert r.json()["code"] == "AUTH_SMS_TOO_FREQUENT"
