from datetime import datetime, timedelta

import pytest
import ulid
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select  # noqa: F401

from app.core.security import issue_access_token
from app.db.session import SessionLocal
from app.deps.redis import get_redis
from app.main import app
from app.models.analysis_task import AnalysisTask, TaskStatus
from app.models.photo import ModerationStatus, Photo
from app.models.user import User
from app.services.analyze_runner import run_analysis
from tests.helpers import TEST_OSS_KEY, make_phone_hash


@pytest.mark.asyncio
async def test_get_report_after_runner():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("reports-get"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        p = Photo(
            user_id=u.id,
            oss_key=TEST_OSS_KEY,
            moderation_status=ModerationStatus.passed,
            expires_at=datetime.utcnow() + timedelta(days=10),
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        tid = str(ulid.new())
        s.add(
            AnalysisTask(
                id=tid,
                user_id=u.id,
                photo_id=p.id,
                status=TaskStatus.queued,
                llm_provider="mock",
            )
        )
        await s.commit()
        uid = u.id

    async for r in get_redis():
        await run_analysis(task_id=tid, redis=r, frame_delay=0)
        break

    tok = issue_access_token(uid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get(
            f"/api/reports/{tid}", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 200
    body = r.json()
    assert body["taskId"] == tid
    assert body["radarScores"]["stype"] == 45
    assert body["state_values"]["stype"] == 82
    assert body["schemaVersion"] == "v1"
    assert body["struct"]["layers"][0]["code"] == "skin"
