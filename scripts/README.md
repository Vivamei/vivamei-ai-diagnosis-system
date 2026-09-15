# scripts/ —— 项目脚本总目录

本仓库所有脚本的清单。多数脚本集中在这里；少数因为要在特定工作目录下运行，
留在了它们必须在的位置（下表已注明原因）。

## 本目录（scripts/）

| 脚本 | 用途 | 怎么跑 |
|------|------|--------|
| `gen-types.sh` | 从运行中的 FastAPI 拉 openapi.json，生成前端 TS 类型到 `packages/shared-types/api.ts` | `bash scripts/gen-types.sh`（API 起在 8080） |
| `gen-frontend-env.mjs` | 把 `config/frontend.env`（唯一真源）按段拆成 `apps/web/.env.production` 与 `apps/miniapp/.env.production` / `.env.development` | 一般不用手动跑，`build:weapp` / `build:h5` / `infra/build.sh` 会自动调；手动：`node scripts/gen-frontend-env.mjs miniapp` |
| `smoke.sh` | 部署后冒烟：健康检查 / OpenAPI / 短信限流 / 验证码错误 / 静态首页 | `HOST=https://<域名> bash scripts/smoke.sh` |
| `backup.sh` | MySQL + Redis 备份并 gpg 加密，cron 每日调用 | `bash scripts/backup.sh`（需 `MYSQL_PASSWORD`/`BACKUP_GPG_PASS`） |
| `export-leads.py` | 留资导出 CSV（按时间区间） | `cd apps/api && poetry run python ../../scripts/export-leads.py --from … --to … --out leads.csv` |
| `init_sensitive_words.py` | 维护敏感词表 `apps/api/app/data/sensitive_words.txt`（增/删/列） | `python scripts/init_sensitive_words.py add "词1" "词2"` |
| `loadtest_analyze.py` | 报告生成压测：N 个虚拟用户同时触发 analyze，量「D 秒内出多少份」 | `cd apps/api && poetry run python ../../scripts/loadtest_analyze.py -c 200 --deadline 120` |
| `gh-link.sh` | 通用 git 关联助手（本项目不用 git，仅备用） | `bash scripts/gh-link.sh` |
| `tee.bat` | 简易 tee：stdin 字节级同时透传到控制台与文件（避免中文乱码） | `some_cmd 2>&1 \| scripts\tee.bat logs\xxx.log` |

> 注意：`gen-types.sh` / `gen-frontend-env.mjs` / `export-leads.py` / `init_sensitive_words.py`
> 都按“脚本在 `scripts/` 下、上一级即仓库根”来定位路径，**不要移进子目录**，否则相对路径会断。

## 不在本目录、但也是脚本（各有其位）

| 脚本 | 位置 | 为什么不放这里 |
|------|------|----------------|
| `start-dev.bat` | 仓库根 | 双击启动入口（含依赖安装），用户在根目录直接双击 |
| `stop-dev.bat` | 仓库根 | 配套停止入口，同上 |
| `make-distribution.bat` | 仓库根 | 用 `%~dp0`（自身目录）当仓库根来打包，必须待在根目录 |
| `build.sh` | `infra/` | 构建并推镜像，读同目录 `infra/build.conf` |
| `mock_llm_server.py` | `apps/api/` | 独立 mock LLM 服务，`make mock-llm` 从 `apps/api` 起 |
