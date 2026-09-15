import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _dek() -> bytes:
    return base64.b64decode(settings.phone_dek_base64)


def _hmac_key() -> bytes:
    return settings.phone_hmac_key.encode()


def encrypt_phone(phone: str) -> str:
    """返回 base64(nonce || ciphertext || tag)。Nonce 每次随机，AAD 固定为 b"phone"。"""
    nonce = os.urandom(12)
    aes = AESGCM(_dek())
    ct = aes.encrypt(nonce, phone.encode(), associated_data=b"phone")
    return base64.b64encode(nonce + ct).decode()


def decrypt_phone(blob: str) -> str:
    raw = base64.b64decode(blob)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(_dek()).decrypt(nonce, ct, associated_data=b"phone").decode()


def hash_phone(phone: str) -> str:
    """HMAC-SHA256(phone) → hex；用于按手机号建立可索引的唯一键。"""
    return hmac.new(_hmac_key(), phone.encode(), hashlib.sha256).hexdigest()
