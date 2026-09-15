from app.services.phone_crypto import decrypt_phone, encrypt_phone, hash_phone


def test_encrypt_then_decrypt_roundtrip():
    phone = "13800138000"
    ct = encrypt_phone(phone)
    assert ct != phone
    assert decrypt_phone(ct) == phone


def test_encrypt_is_non_deterministic():
    assert encrypt_phone("13800138000") != encrypt_phone("13800138000")


def test_hash_is_deterministic():
    h1 = hash_phone("13800138000")
    h2 = hash_phone("13800138000")
    assert h1 == h2
    assert len(h1) == 64


def test_hash_differs_per_phone():
    assert hash_phone("13800138000") != hash_phone("13800138001")
