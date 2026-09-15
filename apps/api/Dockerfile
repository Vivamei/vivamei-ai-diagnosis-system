FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.4 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app
COPY apps/api/pyproject.toml apps/api/poetry.lock* ./
RUN poetry install --without dev --no-root --no-interaction

COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./

# 非敏感基线配置烤进镜像（/app/.env）；运行时 env_file 里的密钥优先级更高会覆盖同名项
COPY config/prod.baseline.env ./.env

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# worker 数由 UVICORN_WORKERS 控制（默认 1，保持单进程内信号量为全局闸门的语义）。
# 突发高并发时调大：全局并发 = UVICORN_WORKERS × ANALYZE_MAX_CONCURRENCY。
# shell 形式 CMD 才能做环境变量展开；未设时回退 1。
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --workers ${UVICORN_WORKERS:-1}
