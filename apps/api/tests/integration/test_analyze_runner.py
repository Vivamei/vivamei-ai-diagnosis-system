from datetime import datetime, timedelta

import pytest
import ulid
from sqlalchemy import select

from app.db.session import SessionLocal
from app.deps.redis import get_redis
from app.models.analysis_task import AnalysisTask, TaskStatus
from app.models.photo import ModerationStatus, Photo
from app.models.report import Report
from app.models.user import User
from app.services.analyze_runner import run_analysis
from tests.helpers import TEST_OSS_KEY, make_phone_hash


@pytest.mark.asyncio
async def test_runner_full_lifecycle():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("analyze-runner"),
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

    async for r in get_redis():
        await run_analysis(task_id=tid, redis=r, frame_delay=0)
        break

    async with SessionLocal() as s:
        t = (
            await s.execute(select(AnalysisTask).where(AnalysisTask.id == tid))
        ).scalar_one()
        assert t.status == TaskStatus.done
        rep = (
            await s.execute(select(Report).where(Report.task_id == tid))
        ).scalar_one()
        assert rep.radar_scores["stype"] == 45
        assert rep.stype["primary"] == "bone"
        assert rep.optimization
