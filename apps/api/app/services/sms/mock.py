from loguru import logger

from app.services.sms.base import SmsProvider


class MockSmsProvider(SmsProvider):
    """开发期占位：不真发短信，仅记录并打 log。"""

    def __init__(self):
        self.last_sent: tuple[str, str] | None = None

    async def send_code(self, phone: str, code: str) -> None:
        self.last_sent = (phone, code)
        masked = phone[:3] + "****" + phone[-4:]
        logger.bind(phone=masked).info("[MOCK SMS] code={}", code)
