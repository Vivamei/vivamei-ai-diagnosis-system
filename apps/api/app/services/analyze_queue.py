import asyncio

from app.core.config import settings

# 单 uvicorn worker（Dockerfile CMD 无 --workers），进程内信号量即可作为全局并发闸门，
# 无需 Redis 分布式锁。拿到槽的任务才真正调 LLM，其余在此排队，避免瞬时打爆下游。
_sem = asyncio.Semaphore(settings.analyze_max_concurrency)
# 尚未拿到并发槽、仍在排队的 task_id，按进入顺序排列，用于算「前面还有几人」。
_waiting: list[str] = []


def register(task_id: str) -> None:
    if task_id not in _waiting:
        _waiting.append(task_id)


def unregister(task_id: str) -> None:
    try:
        _waiting.remove(task_id)
    except ValueError:
        pass


def position(task_id: str) -> int:
    """前面还有几人在排队（不含自己）。不在队列里返回 0。"""
    try:
        return _waiting.index(task_id)
    except ValueError:
        return 0


async def acquire() -> None:
    await _sem.acquire()


def release() -> None:
    _sem.release()
