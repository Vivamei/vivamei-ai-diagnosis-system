# 本地启动手册

从零把 venus-4s 跑起来的完整步骤。Windows / macOS / Linux 通用。

---

## 0. 先决条件（安装一次性）

| 工具 | 版本 | 检查命令 | 安装方式 |
|---|---|---|---|
| **Python** | 3.11.x | `python --version` | [python.org](https://www.python.org/) 或 conda |
| **Poetry** | 1.8+ | `poetry --version` | `pip install poetry==1.8.4` 或参见 [官方安装](https://python-poetry.org/docs/#installation) |
| **Node.js** | 20+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| **pnpm** | 9+ | `pnpm --version` | `corepack enable && corepack prepare pnpm@9 --activate`（Node 20+ 自带 corepack） |
| **Docker Desktop** | 26+ | `docker --version`  | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Git** | 任意 | `git --version` | 任意 |

**Windows 用户额外注意**：所有 shell 命令在 **Git Bash** 或 **WSL** 下跑（不要用 PowerShell / cmd），路径用正斜杠。

---

## 1. 启动数据库与缓存（每次开发前）

```bash
cd C:/work/md_file/weixin/yimei-rfp/venus-4s

# 首先确保 Docker Desktop 已启动（任务栏小鲸鱼图标）
docker info | head -3
# 看到 "Server: Docker Engine ..." 说明 daemon 正常

# 拉起 mysql + redis 容器
make dev
# 或直接：docker compose -f infra/docker-compose.dev.yml up -d

# 等约 10 秒到 healthy
docker compose -f infra/docker-compose.dev.yml ps
# 期望两个 service 都显示 (healthy)
```

**端口占用**：mysql 占 3306，redis 占 6379。本机若已有同端口服务先停掉，或改 `infra/docker-compose.dev.yml` 的 ports 映射。

**停止依赖**：`make dev-stop`（数据保留在 named volume，下次起继续用）。
**清空数据**：`docker compose -f infra/docker-compose.dev.yml down -v`（删卷）。

### 1.1 不想装 Redis？用内存版（fakeredis）

如果暂时不想跑 Redis，在 `config/dev.env` 把 `REDIS_URL` 改成 `memory://`：

```bash
# config/dev.env
REDIS_URL=memory://
```

代码内置 `fakeredis` 兼容层（在 `app/deps/redis.py` 自动切换），所有 Redis 操作（SETEX / INCR / Streams / pipeline）走纯 Python 内存模拟，无需启动 Redis。

**约束**：
- 数据只活在 API 进程里，重启 uvicorn 就清空（短信验证码、SSE buffer 都没了）
- 同一进程内多个 worker 不共享（uvicorn 启动加 `--workers 2+` 就会有数据不一致）
- 仅供本地单人起来看页面 / 调前端，**别用在生产或多进程**

> MySQL 仍然要起，因为表结构和数据持久化不能 mock。如果连 MySQL 也想免，需要把 DATABASE_URL 改 SQLite + aiosqlite 并改 alembic migration 里的 MySQL 专属类型（JSON/Enum），当前不支持。

---

## 2. 后端 API（首次启动）

```bash
cd apps/api

# 一次性安装 Python 依赖（约 2-3 分钟）
poetry install
# 期望：Installing dependencies from lock file
#       Package operations: 60 installs, ...

# 跑数据库迁移（创建 6 张表）
poetry run alembic upgrade head
# 期望：Running upgrade -> 001, 001 -> 002, ..., 005 -> 006

# 启动 API（开发模式自动热重载）
poetry run uvicorn app.main:app --reload --port 8000
```

启动成功标志：
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**验证**：浏览器开 `http://localhost:8000/docs` 应看到 Swagger UI，列出 11 个端点。

```bash
# curl 验证 /health
curl http://localhost:8000/health
# 期望：{"status":"ok"}
```

---

## 3. 前端 H5（另开一个终端）

```bash
cd apps/web

# 安装依赖（约 1-2 分钟）
pnpm install
# 期望：Done in X.Xs

# 启动 Vite dev server
pnpm dev
# 或：make web（从根目录）
```

启动成功标志：
```
VITE v5.x.x ready in XXX ms
➜  Local:   http://localhost:5173/
```

浏览器开 `http://localhost:5173/` 看到 4S 首页就是成功。

**前端代理**：`vite.config.ts` 已配 `/api → http://localhost:8000`，前端直接 fetch `/api/*` 自动透传到后端。

---

## 4. 端到端走一遍（手动）

按 H5 用户流程跑一次：

### 4.1 首页 `/`
- 看到「薇分美学」+「开始测一测」按钮 → 点进去

### 4.2 拍照页 `/capture`
- 弹《隐私协议与人脸采集授权》→ 勾选 → 同意并继续
- 输入手机号（任意 `1[3-9]\d{9}`，例如 `13800138000`）
- 点「发送验证码」
- **去看 API 控制台**，应有一行类似：
  ```
  {"level":"INFO","message":"[MOCK SMS] code=123456","phone":"138****8000"}
  ```
- 把 6 位验证码填进去（自动 verify 后跳到拍照阶段）
- 点「拍照 / 上传照片」（电脑选任意图片）→ 自动压缩 + 上传 + 创建任务

> Mock 模式下 OSS 上传跳过实际 PUT（`accessKeyId` 是 `STS.MOCK_...`），后端记录 OSS key 但不真存图——前端开发足够。

### 4.3 分析页 `/analyzing/:id`
- 看到 4 步进度条 + 4 个维度卡片流式打字（Mock Provider 默认 1s/帧节奏）
- 全部 done 后自动跳到报告页

### 4.4 报告页 `/report/:id`
- 顶部「您的 4S 美学报告」+ AI 角标
- 4S 雷达图 + 4 个维度卡片（可折叠）+ 美学优化方向
- 「保存为长图」生成 PNG 下载；「保存为 PDF」生成 A4 分页 PDF 下载（均带 AIGC 水印）
- 「预约到店面诊」跳留资页（带 taskId）

### 4.5 留资页 `/booking`
- 填姓名 + 手机号 + 可选门店 + 时间 → 提交
- 后端 audit_logs 表会插一行 `booking.create`

### 4.6 法务页
- `/legal/privacy` / `/legal/terms` 查看协议正文（从 `apps/web/public/legal/*.md` 加载）

---

## 5. 后续启动（已装好依赖）

每次开发只需 3 个终端：

```bash
# 终端 1：依赖
make dev

# 终端 2：后端
cd apps/api && poetry run uvicorn app.main:app --reload --port 8000

# 终端 3：前端
cd apps/web && pnpm dev
```

或者从根目录用 Makefile：
```bash
make dev    # 起 docker
make api    # 跑后端（前台）
make web    # 跑前端（前台）— 另开终端
```

### 5.1 LLM Mock 两种模式（本地全流程跑通）

后端不依赖真实大模型也能跑完整链路。两种模式按需选：

**模式 A：进程内 mock（默认，零额外进程）**

`config/dev.env.example` 默认 `LLM_PROVIDER=mock`，后端启动后直接走 `MockLLMProvider`，读 `mock/sample_report.json` 模拟 SSE 事件。

适用：日常开发、前端联调、e2e。

**模式 B：独立 mock HTTP 服务（验证真实 HTTP/SSE 链路）**

模拟同事 LLM 服务的 `POST /v1/analyze` SSE 接口（契约见 `docs/LLM_API_ALIGNMENT.md`）。
启动方式：

```bash
make mock-llm          # 起在 :9000，默认 frame-delay=1s
# 等价：cd apps/api && poetry run python mock_llm_server.py --port 9000
```

然后把 `.env` 切到 qwen provider 模式：
```bash
LLM_PROVIDER=qwen
LLM_QWEN_BASE_URL=http://localhost:9000
```

适用：联调 `QwenLLMProvider` 本身、对照 alignment 文档验证 SSE 帧、自动化压测。

mock 服务支持通过 `userHints.scenario` 触发场景（在前端 `createAnalyze` 里临时塞或直接 `curl` 测）：
- `slow`：phase 间隔 ×3，模拟慢响应
- `error`：第二个 phase 后吐 error 事件
- `banned`：在 style 段注入"医疗治疗"敏感词，验证后端审核拦截

快速验证 mock 服务在跑：
```bash
curl -N -X POST http://localhost:9000/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"schemaVersion":"v1","taskId":"test_001","imageUrl":"http://x/y.jpg"}'
```

---

## 6. 跑测试

```bash
# 后端：单元 + 集成（依赖需先 make dev 起 mysql + redis）
cd apps/api && poetry run pytest -v
# 期望约 30+ 用例全绿

# 前端：vitest 单元
cd apps/web && pnpm test --run

# Lint
cd apps/api && poetry run ruff check . && poetry run mypy app
cd apps/web && pnpm tsc --noEmit
```

---

## 7. 切换 LLM Provider

默认 `LLM_PROVIDER=mock`（读 `mock/sample_report.json` 模拟流式）。

切到同事真实 LLM 服务：
1. 编辑 `config/dev.env`：
   ```
   LLM_PROVIDER=qwen
   LLM_QWEN_BASE_URL=http://<llm-service-host>:8080
   ```
2. 重启 API（`Ctrl+C` 后再 `poetry run uvicorn ...`，dev 模式 .env 改动不会热重载）

> 同事 LLM 服务对外的 HTTP/SSE 协议见 `docs/design/sections/05-llm-contract.md` 5.4 节，与本仓库 `apps/api/app/services/llm/qwen.py` 实现对齐。

---

## 8. 数据库相关

### 查看表

```bash
docker exec -it venus-mysql mysql -uvenus -pdevpass venus
mysql> SHOW TABLES;
+-----------------+
| users           |
| photos          |
| analysis_tasks  |
| reports         |
| bookings        |
| audit_logs      |
| alembic_version |
+-----------------+
mysql> SELECT id, phone_hash, created_at FROM users LIMIT 5;
```

### 重置某张表 / 全量重建

```bash
cd apps/api

# 回退一个版本
poetry run alembic downgrade -1

# 回退到空
poetry run alembic downgrade base

# 重新升到最新
poetry run alembic upgrade head
```

### 新增 migration（修改 model 后）

```bash
poetry run alembic revision --autogenerate -m "add some column"
# 检查 alembic/versions/00X_*.py 生成的内容
poetry run alembic upgrade head
```

---

## 9. Redis 相关

```bash
docker exec -it venus-redis redis-cli
127.0.0.1:6379> KEYS sms:*
127.0.0.1:6379> KEYS task:stream:*
127.0.0.1:6379> XRANGE task:stream:01HW9... - +    # 看 SSE 事件
127.0.0.1:6379> FLUSHDB                            # ⚠️ 清空当前 db
```

---

## 10. 常见问题

### Q: `make dev` 报 `failed to connect to docker daemon`
→ Docker Desktop 没启动。手动启 Docker Desktop 应用，等右下角小鲸鱼变绿。

### Q: `poetry install` 卡很久
→ 国内网络下用清华源：
```bash
poetry config repositories.tsinghua https://pypi.tuna.tsinghua.edu.cn/simple
# 在 pyproject.toml 加 [[tool.poetry.source]] 配置
```
或临时：
```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
poetry install
```

### Q: `pnpm install` 慢
→ 用淘宝镜像：
```bash
pnpm config set registry https://registry.npmmirror.com
pnpm install
```

### Q: 前端报 `502 Bad Gateway` 或 `/api/*` 404
→ 后端没起，或起在了非 8000 端口。检查 `apps/web/vite.config.ts` 的 proxy 配置。

### Q: 浏览器看 `/api/auth/sms/send` 返回 500
→ 看 API 控制台错误日志。最常见：MySQL 没 migrate（执行 `alembic upgrade head`）。

### Q: SSE 流式只看到一个事件就断
→ Vite dev 默认不缓冲流式，应该正常。检查浏览器 Network 看 EventStream 是否一直在收 frame。

### Q: alembic 报 `Target database is not up to date`
→ 表已存在但 alembic_version 表没记录。`poetry run alembic stamp head` 后再 upgrade。

### Q: 上传后跳到 analyzing 页一直没动
→ 检查 API 日志，最可能是 LLM Provider 配错。默认 `LLM_PROVIDER=mock` 应该立即出报告。

---

## 11. 关闭

```bash
# 关前端：Ctrl+C
# 关后端：Ctrl+C
# 关依赖（保留数据）
make dev-stop
# 完全销毁（连数据一起）
docker compose -f infra/docker-compose.dev.yml down -v
```

---

## 12. 文件参考

- 设计稿（架构 / DB / API / LLM 契约 / 合规）：`docs/design/design.md`
- 生产部署：`docs/02-部署实施.md`
- 运维手册：`docs/04-日常运维与排查.md`
