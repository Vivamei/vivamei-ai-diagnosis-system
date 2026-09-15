# 第 8 段：测试、CI/CD、部署与监控

## 8.1 测试策略

**优先级倒挂——根据 5 万版 3.5 周工期，不追求 100% 覆盖率**：测能挡住的 bug，不为测试而测试。

```
                ┌─────────────────────────────────┐
                │  E2E (Playwright)               │  ~5 个核心路径
                │  - 拍照→分析→报告→留资              │
                │  - SMS 登录                      │
                └─────────────────────────────────┘
              ┌────────────────────────────────────┐
              │ 集成测试 (pytest + httpx)            │ ~30 个用例
              │ - API 全部 endpoint 黄金路径          │
              │ - 限流 / 鉴权 / 错误码              │
              │ - SSE 流式（mock LLM）              │
              └────────────────────────────────────┘
            ┌─────────────────────────────────────┐
            │ 单元 (pytest)                        │ ~50 个用例
            │ - LLM Provider 转译                  │
            │ - 敏感词过滤                          │
            │ - 手机号加解密 / phone_hash           │
            │ - JWT issue/verify                  │
            └─────────────────────────────────────┘
```

**前端测试**：放弃组件单测，只做 Playwright E2E（覆盖 5 条核心路径）+ `@testing-library/react` 测 3 个最复杂组件（`RadarChart` / `useSse` / `ConsentDialog`）。

**专项验收**：
- **合规专项**：上线前跑 1 次"高敏词模拟全链路"，覆盖 R3/R8/R10 路径
- **压测**：locust 模拟 100 并发拍照→分析，验证 P95 < 500ms（除流式 SSE 外的同步接口）
- **跨端**：iOS 15+/16+/17、Android 11+/13+、微信 8.0 三档真机各跑一遍

## 8.2 CI/CD

**Git 工作流**：trunk-based（main + feature branch）。无 release 分支，main 即可发布。

```yaml
# .github/workflows/ci.yml 概览
on: [push, pull_request]

jobs:
  api:
    - poetry install
    - poetry run ruff check
    - poetry run mypy
    - poetry run pytest --cov  (要求 ≥ 70%)
    - alembic upgrade head (against ephemeral mysql)

  web:
    - pnpm install
    - pnpm tsc --noEmit
    - pnpm lint
    - pnpm build           (验证 bundle ≤ 80KB gzip)

  e2e:
    - 启 docker-compose（api + mock-llm + mysql + redis + web）
    - pnpm playwright test --reporter=html
```

**部署流**（main 分支合入即触发）：

```
GitHub Actions
  ├─ build api Docker image → 推私有镜像仓库（阿里云 ACR）
  ├─ build web 静态产物 → 上传到 ECS:/srv/venus-4s/web/dist/
  └─ ssh ECS:
       cd /srv/venus-4s
       git pull && docker compose pull
       docker compose up -d api          # 滚动重启 api
       nginx -s reload                   # 静态产物已替换
       ./scripts/smoke.sh                # 5 个 curl 验通过率
       回滚: docker compose up -d api:previous
```

**密钥管理**：
- `infra/.env.example` 列全 30 个变量，不含真值
- 生产 `.env` 放 ECS `/etc/venus-4s/`（root 600 权限），不进 git
- 阿里云 AK/SK 用 STS 临时凭证，主 AK 入 KMS 不出现在 .env

## 8.3 部署架构（单机 ECS）

**机型**：阿里云 ECS 4核8G + 100G ESSD + 5M 带宽。月成本约 ¥250。

> 落地时收敛成了 `infra/docker-compose.ecs.yml`：**MySQL/Redis 改用阿里云托管
> RDS/KVStore，不在 compose 里起容器**；nginx 也不再是独立服务，而是烤进 web 镜像，
> 由 `infra/nginx/edge.conf` 挂载做 TLS 终止 + 反代 `/api`。下面是实际在跑的三个容器。

```yaml
# infra/docker-compose.ecs.yml 概览
services:
  web:          # 静态站 + 443 TLS 终止 + 反代 /api（含 SSE / WS）
    image: ${WEB_IMAGE}
    ports: ["80:80","443:443"]
    volumes:
      - ./nginx/edge.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on: [api]

  api:          # FastAPI + uvicorn
    image: ${API_IMAGE}
    env_file: /etc/venus-4s/.env
    expose: ["8000"]
    restart: always
    healthcheck:
      test: curl -f localhost:8000/health || exit 1

  cron:         # 定时任务：照片清理、日志归档
    image: ${API_IMAGE}
    command: ["python","-m","app.cron"]
    env_file: /etc/venus-4s/.env
```

**Nginx 关键配置**：
- HTTP→HTTPS 强跳 + HSTS（max-age=31536000）
- 静态资源 1 年缓存（hash 文件名），index.html 不缓存
- `/api/analyze/*/stream` 走 SSE：`proxy_buffering off; proxy_read_timeout 3600s`
- `client_max_body_size 6m`（兜底，正常走 OSS 直传）
- 全站 gzip + brotli

## 8.4 监控与报警

5 万版预算不上 Grafana/Prometheus，用最轻方案：

| 监控项 | 方式 | 阈值 |
|---|---|---|
| 系统资源 | 阿里云云监控（白嫖） | CPU > 80% / 内存 > 85% / 磁盘 > 80% 报警 |
| API 错误率 | 阿里云日志服务 SLS（按量付费，很便宜） | 5xx > 1% / min 报警 |
| LLM 失败率 | SLS 关键字 `LLM_TIMEOUT / LLM_UNAVAILABLE` | 5min 内 > 10 次报警 |
| 内容安全拒绝率 | SLS 关键字 `moderation_rejected` | 1h 内 > 30 次报警（疑似攻击或词库需调） |
| SSE 断连率 | 自埋点写日志，SLS 聚合 | > 5% 报警 |
| 业务指标 | 当日测评数 / 留资数 / 转化率 | 每日 9 点日报飞书/邮件 |

**报警通道**：飞书机器人（默认）+ 短信兜底。

## 8.5 数据备份

- MySQL：mysqldump 每天凌晨 3 点 → 加密 → 上传 OSS（保留 30 天）
- Redis：appendonly 持久化，每日 0 点 BGSAVE → OSS
- 上传脚本：`scripts/backup.sh`，挂 cron

## 8.6 灰度与回滚

5 万版不上灰度系统。Docker tag 留两版本（`:current` 和 `:previous`），回滚就是 1 行 `docker compose up -d api:previous`，5 分钟内可完成。
