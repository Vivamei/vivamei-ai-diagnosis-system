import time

import ulid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        *,
        retryable: bool = False,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(ulid.new())
        request.state.request_id = rid
        client = (
            f"{request.client.host}:{request.client.port}" if request.client else "-"
        )
        query = request.url.query
        log = logger.bind(request_id=rid)
        # 收到请求即记一行（含 query string），无论后续成功/异常都能定位入口。
        log.info(
            "[req] --> {method} {path}{qs} client={client} request_id={rid}",
            method=request.method,
            path=request.url.path,
            qs=f"?{query}" if query else "",
            client=client,
            rid=rid,
        )
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = rid
        log.info(
            "[req] <-- {method} {path} {status} {ms:.1f}ms client={client} request_id={rid}",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=elapsed_ms,
            client=client,
            rid=rid,
        )
        return response


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        rid = getattr(request.state, "request_id", "")
        client = f"{request.client.host}:{request.client.port}" if request.client else "-"
        log = logger.bind(request_id=rid)
        msg = (
            "[AppError] {method} {path} -> {status} code={code} message={message} "
            "client={client} request_id={rid}"
        )
        fields = dict(
            method=request.method,
            path=request.url.path,
            status=exc.status_code,
            code=exc.code,
            message=exc.message,
            client=client,
            rid=rid,
        )
        # 5xx 视为服务端异常，4xx 视为可预期的业务/校验拒绝
        if exc.status_code >= 500:
            log.error(msg, **fields)
        else:
            log.warning(msg, **fields)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "requestId": rid,
                "retryable": exc.retryable,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unknown(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", "")
        client = f"{request.client.host}:{request.client.port}" if request.client else "-"
        logger.bind(request_id=rid).opt(exception=exc).error(
            "[Unhandled] {method} {path} -> 500 client={client} request_id={rid}",
            method=request.method,
            path=request.url.path,
            client=client,
            rid=rid,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "internal server error",
                "requestId": rid,
            },
        )
