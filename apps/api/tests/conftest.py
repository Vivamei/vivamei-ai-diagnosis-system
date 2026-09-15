"""Shared pytest configuration.

Windows 本地跑集成测试的适配（CI/Linux 不受影响）：

1) Selector 事件循环替代默认 Proactor —— Proactor 在关闭已回收的 loop 上关
   aiomysql/redis 连接时会抛 "'NoneType' object has no attribute 'send'"。
2) 全局 async engine / redis 连接池是进程级单例，若 pytest-asyncio 给每个测试
   新建/销毁事件循环，池里的连接会绑在已关闭的 loop 上 → 跨测试污染、
   RUNNER_EXCEPTION、"Event loop is closed"。故这里把事件循环提升为 session 级，
   全程共用一个 loop，与全局 engine/pool 生命周期对齐。
3) APP_ENV=test 在导入 app.core.config 之前就落到环境变量里：settings.is_mocked()
   见到 test 会把所有子系统一律当 mock，跑测试不会误发真短信、不会写真 OSS、
   不会调真模型，也不用为跑测试单独改 config/dev.env。
4) 每轮测试前后回收测试用户（见 _purge_test_users）：集成测试跑的就是本地 dev 库，
   上一轮跑挂在半路的 users 行会留下来，下一轮撞 uk_phone_hash 报 1062，
   真实失败原因被这个重复键掩盖。
"""
import asyncio
import os
import sys

import pytest

os.environ["APP_ENV"] = "test"

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# 删除顺序即外键依赖的逆序：reports→bookings→analysis_tasks→photos→audit_logs→users。
# analysis_tasks.photo_id 指向 photos，所以 tasks 必须先于 photos。
_PURGE_STATEMENTS = (
    "DELETE FROM reports WHERE task_id IN "
    "(SELECT id FROM analysis_tasks WHERE user_id IN :ids)",
    "DELETE FROM bookings WHERE user_id IN :ids",
    "DELETE FROM analysis_tasks WHERE user_id IN :ids",
    "DELETE FROM photos WHERE user_id IN :ids",
    "DELETE FROM audit_logs WHERE actor_id IN :ids",
    "DELETE FROM users WHERE id IN :ids",
)


def _purge_test_users() -> None:
    """删掉带测试前缀的 users 及其依赖行。

    刻意用同步 pymysql 连接、且用完即弃：全局 async engine 的连接池是进程级单例，
    在会话钩子里碰它会把连接绑到 pytest-asyncio 之外的事件循环上，之后每个用例都报
    "attached to a different loop"。清库跟被测代码本来也没有共享连接的必要。
    """
    from sqlalchemy import bindparam, create_engine, text

    from app.core.config import settings
    from tests.helpers import TEST_PHONE_HASH_PREFIX

    engine = create_engine(settings.database_url.replace("+aiomysql", "+pymysql"))
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id FROM users WHERE phone_hash LIKE :p"),
                {"p": f"{TEST_PHONE_HASH_PREFIX}%"},
            )
            ids = [r[0] for r in rows]
            if not ids:
                return
            for sql in _PURGE_STATEMENTS:
                conn.execute(
                    text(sql).bindparams(bindparam("ids", expanding=True)), {"ids": ids}
                )
    finally:
        engine.dispose()


def pytest_sessionstart(session):
    # 跑前先清：上一轮崩在半路留下的行，正是下一轮 1062 的来源。
    _purge_test_users()
    # 落一张测试图：test 环境 OSS 恒为 mock（file 方式），runner 要回读本地字节。
    from tests.helpers import seed_local_object

    seed_local_object()


def pytest_sessionfinish(session, exitstatus):
    # 跑后再清一次，别把残留留给下一个人。
    _purge_test_users()


@pytest.fixture(scope="session", autouse=True)
async def _dispose_engine_at_end():
    yield
    from app.db.session import engine

    await engine.dispose()

