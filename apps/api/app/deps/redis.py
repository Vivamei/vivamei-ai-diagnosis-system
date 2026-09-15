from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

# 真实 Redis 连接池（生产/有 Redis 时使用）
_pool: ConnectionPool | None = None

# fakeredis 单例 server（无 Redis 本地开发时使用）
# REDIS_URL 形如 "memory://" 时走这条分支，所有 get_redis 共享同一份数据
_fake_server = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url, max_connections=settings.redis_max_connections
        )
    return _pool


def _get_fake_server():
    """惰性初始化 fakeredis 的内存 server，所有 client 共享同一份数据。"""
    global _fake_server
    if _fake_server is None:
        # 延迟 import 避免生产环境强依赖 fakeredis
        from fakeredis import FakeServer

        _fake_server = FakeServer()
    return _fake_server


def new_redis() -> Redis:
    """非请求上下文（如 lifespan 启动重放）用的 async Redis client。

    与 get_redis 同源（共享同一 _pool / fakeredis server），但不是依赖、不自动关闭——
    调用方负责在用完后 await client.aclose()。memory:// 时返回 fakeredis。
    """
    if settings.redis_url.startswith("memory://"):
        from fakeredis import FakeAsyncRedis

        return FakeAsyncRedis(server=_get_fake_server())
    return Redis(connection_pool=_get_pool())


async def get_redis():
    """FastAPI 依赖：yield 一个 async Redis client。

    REDIS_URL 以 "memory://" 开头时返回 fakeredis（仅供本地开发，纯内存、进程退出即失效）。
    其它情况走真实 Redis（redis://...）。
    """
    if settings.redis_url.startswith("memory://"):
        from fakeredis import FakeAsyncRedis

        r = FakeAsyncRedis(server=_get_fake_server())
        try:
            yield r
        finally:
            await r.aclose()
        return

    r = Redis(connection_pool=_get_pool())
    try:
        yield r
    finally:
        await r.close()
