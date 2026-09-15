from app.services.oss import generate_object_key


def test_object_key_format():
    k = generate_object_key("user123")
    # uploads/YYYY/MM/DD/{uuid}.jpg
    assert k.startswith("uploads/")
    parts = k.split("/")
    assert len(parts) == 5
    assert parts[4].endswith(".jpg")
    assert len(parts[4]) > 36  # uuid (36 chars) + .jpg


def test_object_key_unique():
    a = generate_object_key()
    b = generate_object_key()
    assert a != b
