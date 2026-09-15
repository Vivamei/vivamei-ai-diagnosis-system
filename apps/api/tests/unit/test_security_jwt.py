import pytest
from jose.exceptions import ExpiredSignatureError

from app.core.security import (
    decode_token,
    issue_access_token,
    issue_refresh_token,
)


def test_issue_and_decode_access():
    tok = issue_access_token(user_id=42)
    claims = decode_token(tok)
    assert claims["sub"] == "42"
    assert claims["type"] == "access"


def test_refresh_token_type():
    tok = issue_refresh_token(user_id=7)
    claims = decode_token(tok)
    assert claims["type"] == "refresh"


def test_decode_expired():
    # 直接签一个已经过期的 token，而不是签 1 秒再 sleep：exp 和校验侧的 now 都按整秒
    # 截断，sleep(1.2) 只有在起始时刻的小数部分够大时才能真正跨过那一秒，
    # 否则 exp == now 判定为未过期 —— 表现为时灵时不灵的 DID NOT RAISE。
    tok = issue_access_token(user_id=1, ttl_seconds=-60)
    with pytest.raises(ExpiredSignatureError):
        decode_token(tok)
