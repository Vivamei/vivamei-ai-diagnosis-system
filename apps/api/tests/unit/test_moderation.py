import pytest

from app.services.moderation import scan_image_mock, scan_text_mock


@pytest.mark.asyncio
async def test_scan_image_passes_normal():
    r = await scan_image_mock("uploads/2026/06/29/abc.jpg")
    assert r.passed is True


@pytest.mark.asyncio
async def test_scan_image_rejects_trigger():
    r = await scan_image_mock("uploads/REJECT.jpg")
    assert r.passed is False
    assert r.raw["label"] == "violation"


@pytest.mark.asyncio
async def test_scan_text_detects_banned():
    r = await scan_text_mock("此项目保证治愈您的痘痘")
    assert r.passed is False
    assert "保证治愈" in r.raw["hits"]


@pytest.mark.asyncio
async def test_scan_text_clean():
    r = await scan_text_mock("您的皮肤状态良好，建议保持")
    assert r.passed is True
