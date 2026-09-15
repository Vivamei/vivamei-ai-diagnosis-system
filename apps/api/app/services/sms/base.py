from abc import ABC, abstractmethod


class SmsProvider(ABC):
    """SMS 提供商抽象。dev/test 用 MockSmsProvider，prod 用 AliyunSmsProvider。"""

    @abstractmethod
    async def send_code(self, phone: str, code: str) -> None: ...
