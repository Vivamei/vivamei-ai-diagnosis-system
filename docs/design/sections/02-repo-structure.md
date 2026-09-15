# 第 2 段：Monorepo 目录结构

> 本段描述**当前实际结构**。与设计初稿的差异（新增小程序端、路由拆分、compose 分三套）已在下方「与初稿的差异」列出。

```
yimei-4s/
├─ apps/
│  ├─ web/                        # React + Vite H5 前端
│  │  ├─ src/
│  │  │  ├─ pages/
│  │  │  │  ├─ Entry.tsx          # 落地/入口分流
│  │  │  │  ├─ Home.tsx           # P1 首页
│  │  │  │  ├─ Login.tsx          # 手机号 + 短信验证码
│  │  │  │  ├─ Capture.tsx        # P2 拍照/上传
│  │  │  │  ├─ Analyzing.tsx      # P3 分析中（SSE）
│  │  │  │  ├─ Report.tsx         # P4 4S 报告
│  │  │  │  ├─ RadarDetail.tsx    # P5 雷达图维度详情
│  │  │  │  ├─ Booking.tsx        # P6 留资/预约
│  │  │  │  ├─ LegalPage.tsx      # 协议渲染壳
│  │  │  │  └─ legal/             #   协议正文
│  │  │  ├─ components/           # RadarChart / DimensionCard / ConsentDialog /
│  │  │  │                        # AiBadge / PhotoCapture / StreamingText / ReportExport …
│  │  │  ├─ api/                  # 调用后端的 fetch 封装
│  │  │  ├─ hooks/                # useAnalyzeStream / useCountdown 等
│  │  │  ├─ contexts/             # 登录态等全局上下文
│  │  │  ├─ config/               # 文案与常量（COPY 等）
│  │  │  └─ styles/               # tokens.css（沿用原型 HTML 的色板）
│  │  ├─ index.html
│  │  ├─ vite.config.ts
│  │  └─ package.json
│  ├─ miniapp/                    # Taro 微信小程序（复用同一套后端接口）
│  │  └─ src/
│  │     ├─ pages/                # home / login / capture / analyzing / report
│  │     ├─ components/           # RadarChart 等（小程序 canvas 版）
│  │     ├─ api/ hooks/ config/   # 与 web 同构
│  │     └─ utils/                # nav / 登录跳转等小程序特有封装
│  └─ api/                        # FastAPI 后端
│     ├─ app/
│     │  ├─ main.py               # uvicorn 入口
│     │  ├─ cron.py               # 定时任务入口（cron 容器）
│     │  ├─ core/                 # config / logging / exceptions / security / audit
│     │  ├─ deps/                 # FastAPI 依赖注入（auth/db/redis）
│     │  ├─ db/                   # base.py / session.py（async engine + session）
│     │  ├─ routers/
│     │  │  ├─ auth.py            # POST /sms/send /sms/verify
│     │  │  ├─ upload.py          # POST /upload/token
│     │  │  ├─ photos.py          # 照片元数据
│     │  │  ├─ analyze.py         # POST /analyze + GET /analyze/{id}/stream (SSE) + /ws
│     │  │  ├─ reports.py         # GET /reports/{id}
│     │  │  ├─ bookings.py        # POST /bookings
│     │  │  ├─ meta.py            # 前端配置/字典
│     │  │  ├─ admin.py           # 内部运维接口
│     │  │  └─ health.py          # GET /health
│     │  ├─ services/
│     │  │  ├─ llm/               # LLM Provider 抽象（base/factory/mock/qwen，见第 5 段）
│     │  │  ├─ sms/               # 短信 Provider 抽象（base/aliyun/mock）
│     │  │  ├─ analyze_queue.py   # 分析任务排队
│     │  │  ├─ analyze_runner.py  # 分析任务执行
│     │  │  ├─ sse_buffer.py      # SSE 分片缓冲/断线续传
│     │  │  ├─ recovery.py        # 中断任务恢复
│     │  │  ├─ oss.py             # 阿里云 OSS STS 凭证 + 直传校验（关闭时落 var/uploads）
│     │  │  ├─ moderation.py      # 阿里云内容安全
│     │  │  ├─ sensitive_words.py # 敏感词过滤
│     │  │  ├─ phone_crypto.py    # 手机号加密存储
│     │  │  ├─ wechat.py          # 小程序登录
│     │  │  └─ ratelimit.py       # Redis 限流
│     │  ├─ models/               # SQLAlchemy ORM
│     │  ├─ schemas/              # Pydantic（请求/响应）
│     │  ├─ data/                 # sensitive_words.txt 等随包数据
│     │  └─ scripts/              # export_users.py / export_bookings.py
│     ├─ alembic/                 # 数据库迁移
│     ├─ var/                     # OSS 关闭时的本地上传目录（运行时，不入库）
│     ├─ tests/
│     ├─ pyproject.toml
│     └─ Dockerfile
├─ packages/
│  └─ shared-types/               # 接口契约
│     ├─ index.ts                 # 从 FastAPI OpenAPI 生成 + 手写补充
│     └─ llm.ts                   # 与 LLM 服务方约定的 schema
├─ config/                        # 集中配置（dev.env / prod.baseline.env / prod.secrets.example）
├─ infra/
│  ├─ build.sh                    # 构建并推 ACR，读同目录 build.conf
│  ├─ docker-compose.dev.yml      # 本地依赖：mysql + redis
│  ├─ docker-compose.ecs.yml      # 生产主线：web / api / cron（db 走托管 RDS/KVStore）
│  ├─ nginx/
│  │  ├─ edge.conf                # 挂进 web 容器：TLS 终止 + SPA + 反代 /api（含 SSE/WS）
│  │  ├─ web.conf                 # 烤进 web 镜像的内层静态服务，不涉及 /api
│  │  └─ ssl/                     # .gitignore
│  ├─ k8s/                        # ACK yaml
│  └─ k3s/                        # 单机 k3s 一键部署
├─ mock/                          # mock LLM 的样例报告，与代码分离
├─ scripts/                       # 所有脚本总目录，见 scripts/README.md
├─ docs/                          # 部署主线 01~04 + design / plans / references
├─ logs/  _local/                 # 运行时日志 / 本地产物，不入库不打包
├─ pnpm-workspace.yaml            # web + miniapp + packages/*；api 独立 poetry
├─ Makefile
└─ README.md
```

## 说明

- **`packages/shared-types`** 不是为了让 Python 共享，而是从 FastAPI 自动生成的 OpenAPI 给前端用。脚本 `gen-types.sh` 跑 `openapi-typescript`，前端 fetch 强类型
- **`apps/api` 用 poetry**，**`apps/web` / `apps/miniapp` 用 pnpm workspace**——两边各自的最佳实践，monorepo 不强行统一包管理器
- **`apps/miniapp` 与 `apps/web` 同构**：`api/`、`hooks/`、`config/` 目录职责一一对应，两端共用同一套后端接口和文案常量；差异只在渲染层（小程序无 SVG，雷达图用 canvas 重画）
- **没建 `apps/admin`**：本期不做后台，留资导出走 `scripts/export-leads.py` 与 `app/scripts/export_*.py`

## 与初稿的差异

| 初稿 | 现状 | 原因 |
|---|---|---|
| 只有 web | 新增 `apps/miniapp` | 增加微信小程序端 |
| `routers/report.py` `booking.py` | `reports.py` `bookings.py`，另加 `photos/meta/admin/health` | 路由按资源复数命名，接口面扩大 |
| `services/sms.py` | `services/sms/` 包 | 与 `llm/` 一样做了 Provider 抽象（aliyun / mock） |
| `infra/docker-compose.yml` 一套 | `dev`（本地依赖）+ `ecs`（生产主线）两套 | 生产 db 改用托管 RDS/KVStore，不再自建容器 |
| 独立 nginx 容器 + scp `dist` 到宿主机 | nginx 烤进 web 镜像，`edge.conf` 挂载 | 前端也走镜像发布，宿主机上不再有静态目录 |
| `shared-types/api.ts` | `index.ts` + `llm.ts` | 生成产物入口改名 |

## 两条并行的交付路径

同一份仓库同时服务两个场景，改目录结构时两边都不能碰坏：

| 场景 | 入口 | 依赖 |
|---|---|---|
| 本地 Windows 开发 | 根目录 `start-dev.bat` / `stop-dev.bat`，打包用 `make-distribution.bat` | poetry + pnpm；MySQL/Redis 走 `docker-compose.dev.yml` 或本机服务 |
| 线上 ECS | `infra/build.sh` 打镜像推 ACR → `docker-compose.ecs.yml` | 托管 RDS/KVStore + `/etc/venus-4s/.env` |

所以根目录那三个 `.bat` **必须留在根目录**（`make-distribution.bat` 用 `%~dp0` 当仓库根），
而 `infra/` 只服务线上。两边共用的是 `config/`、`scripts/`、`apps/`。
