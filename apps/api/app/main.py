import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import RequestIdMiddleware, install_exception_handlers
from app.core.logging import configure_logging
from app.core.preflight import run_preflight
from app.deps.redis import new_redis
from app.routers import admin, analyze, auth, bookings, health, meta, photos, reports, upload
from app.services.recovery import recover_inflight_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level="DEBUG" if settings.app_debug else "INFO")
    # 配置自检必须在建连之前：生产漏配（如短信没配、还在读 mock 报告）直接拒绝启动，
    # 而不是带着降级悄悄跑起来。放行名单见 ALLOW_MOCK。
    run_preflight()

    # 重启重放：扫 DB 里卡在 queued/streaming 的在途分析任务，重新跑完（多 worker 用 Redis
    # claim 去重）。memory:// 本地开发跳过——fakeredis 重启即失效、且 --reload 频繁重启会误重放。
    recovery_redis = None
    if not settings.redis_url.startswith("memory://"):
        recovery_redis = new_redis()
        # 非阻塞，避免拖慢启动；重放出的 run_analysis 复用此 client，故存活到进程退出
        app.state.recovery_redis = recovery_redis
        app.state.recovery_task = asyncio.create_task(
            recover_inflight_tasks(recovery_redis)
        )
    try:
        yield
    finally:
        if recovery_redis is not None:
            await recovery_redis.aclose()



app = FastAPI(title="Yimei 4S API", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)
# CORS 放在最外层（Starlette 后加的中间件更靠外），异常响应才带得上跨域头，
# 否则前端只看到一个没有 CORS 头的 500，拿不到真实错误码。留空白名单则整个不挂。
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
install_exception_handlers(app)
app.include_router(health.router)
app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(photos.router)
app.include_router(analyze.router)
app.include_router(reports.router)
app.include_router(bookings.router)
app.include_router(admin.router)
