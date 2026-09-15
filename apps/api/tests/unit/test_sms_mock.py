import pytest

from app.services.sms.mock import MockSmsProvider


@pytest.mark.asyncio
async def test_mock_sends_and_records():
    p = MockSmsProvider()
    await p.send_code("13800138000", "123456")
    assert p.last_sent == ("13800138000", "123456")
