from typing import Literal

from pydantic import BaseModel, Field


class SmsSendRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    scene: Literal["login", "booking"] = "login"


class SmsSendResponse(BaseModel):
    expiresIn: int = 300


class SmsVerifyRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., pattern=r"^\d{6}$")
    consentVer: str
    username: str | None = Field(default=None, min_length=1, max_length=32)


class UserBrief(BaseModel):
    id: int
    nickname: str | None


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    user: UserBrief


class RefreshRequest(BaseModel):
    refreshToken: str


class AccessResponse(BaseModel):
    accessToken: str
    expiresIn: int


class LogoutRequest(BaseModel):
    refreshToken: str


class WxLoginRequest(BaseModel):
    """wx.login 拿到的一次性 code。"""

    code: str = Field(..., min_length=1, max_length=128)


class WxLoginResponse(BaseModel):
    """openid 已绑定用户则直接返回 tokens；否则 needPhone=true，前端弹手机号授权。"""

    needPhone: bool
    bindToken: str | None = None
    tokens: TokenPair | None = None


class WxPhoneRequest(BaseModel):
    """<button open-type="getPhoneNumber"> 回调的 code + wx/login 下发的 bindToken。"""

    bindToken: str = Field(..., min_length=1)
    phoneCode: str = Field(..., min_length=1, max_length=256)
    consentVer: str
    username: str | None = Field(default=None, min_length=1, max_length=32)
