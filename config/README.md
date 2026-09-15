# config/ —— 全项目配置集中地

所有环境配置都在这一个文件夹，不用再去 `apps/api/`、`infra/` 到处找。

| 文件 | 用途 | 谁读它 |
|------|------|--------|
| `dev.env` | 本地开发实际配置（真实可用值） | 后端 `app/core/config.py`（本地启动时） |
| `dev.env.example` | 本地开发配置模板 | 新人复制成 `dev.env` 参考填写 |
| `prod.baseline.env` | 生产「非敏感」基线，构建时烤进 api 镜像 `/app/.env` | `apps/api/Dockerfile`、`infra/build.sh` |
| `prod.secrets.example` | 生产「密钥」模板（DB/Redis 口令、JWT、手机号加解密、阿里云 AK） | 部署时复制到服务器 `/etc/venus-4s/.env` 填真实值 |

## 配置优先级（pydantic）

运行时「环境变量 / env_file」 > 镜像内 `/app/.env`（基线）。
即：`prod.secrets.example` 里的密钥在运行时注入，会覆盖 `prod.baseline.env` 的同名基线项。

推论（部署时最省事的一条）：**改密钥/开关只要重启容器，改基线才要重新打镜像。**
所以小程序从内测转正式（填 `WX_APPID`/`WX_SECRET`、去掉 `ALLOW_MOCK` 里的 `wechat`）
只需改服务器上的 `/etc/venus-4s/.env` 再 `up -d`，不用重新构建。

## mock 与真实服务：谁决定走哪条路

**`ALLOW_MOCK` 一处说了算**，所有环境同一套规则：

- 列进 `ALLOW_MOCK` 的子系统 → 按 mock 跑（即使凭据已配齐）。
- 没列进来的 → 必须走真实服务，凭据缺失直接**拒绝启动**（fail-fast）。

它既是「开关」也是「放行条」，所以列了 `llm` 就不用再把 `LLM_PROVIDER` 改成 `mock`、
列了 `oss` 就不用再动 `OSS_ENABLED`——一个子系统只由这一处决定。反过来，`llm` **没**列进
名单时 `LLM_PROVIDER` 完全说了算，想指定 `sync` / `queue` / `async` 照填不误。

| 子系统 | 名字 | 走真实服务还需要 | 走 mock 时的行为 |
|--------|------|------------------|------------------|
| 短信 | `sms` | `ALI_ACCESS_KEY_ID` + `ALI_ACCESS_KEY_SECRET` + `ALI_SMS_SIGN` + `ALI_SMS_TEMPLATE_LOGIN` 四项全齐 | 仅 `SMS_TEST_PHONE_PREFIX`(133) 开头的号能登录，验证码恒为 `SMS_TEST_CODE`(100000) |
| 微信小程序 | `wechat` | `WX_APPID` + `WX_SECRET` 都非空 | openid 由 `wx.login` 的 code 派生（换台机器就变），授权手机号返回 133 开头的假号 |
| 大模型 | `llm` | `LLM_PROVIDER` 取 `async`/`sync`/`queue`，且对应 base_url 指向真实服务 | 所有报告都读 `apps/api/mock/sample_report.json`，内容与本人无关 |
| 内容审核 | `moderation` | `MODERATION_ENABLED=true` | 图片只按 object_key 含 `REJECT` 判违规、文本只匹配几个固定词，等同没有机审 |
| OSS | `oss` | `OSS_ENABLED=true` + bucket/endpoint/AK 齐全 | 上传走 file 方式：原图落容器本地 `var/uploads/`，容器重建即丢，多实例互相读不到 |

> ⚠️ `MODERATION_ENABLED=true` 目前会让上传照片直接报错：`app/services/moderation.py`
> 的 `scan_image` / `scan_text` 还是 `raise NotImplementedError`。接入阿里云 Green
> 之前必须保持 `false`，并把 `moderation` 列进 `ALLOW_MOCK`。

各档位的名单：

| 文件 | `ALLOW_MOCK` | 含义 |
|------|--------------|------|
| `dev.env.example`（新人零配置） | `sms,wechat,llm,moderation,oss` | 全 mock，clone 下来不配任何云端账号就能跑 |
| `dev.env`（你自己的） | 按实际接通情况填 | 接通哪个就把哪个从名单里去掉，立刻走真实服务 |
| `prod.baseline.env` | `wechat,moderation` | 内测期只放行这两项，其余漏配即拒绝启动 |

唯一例外是 `APP_ENV=test`：自动化测试视同全 mock，跑 pytest 不用维护名单，
也不会误发真短信 / 误传真 OSS（`apps/api/tests/conftest.py` 已自动设好）。

## `ALLOW_MOCK` —— mock 放行名单

降级本身只打一行 warning，漏配一项没人会发现，直到用户收不到短信才暴露。
所以加了一道 fail-fast：**任何仍在 mock 且不在 `ALLOW_MOCK` 里的子系统，
都会让 api 拒绝启动**。列进名单 = 明知故犯并已接受后果。

可选值：`sms` `wechat` `llm` `moderation` `oss`（逗号分隔）。

当前基线 `ALLOW_MOCK=wechat,moderation`，两项都是有意为之：

- `wechat` —— 小程序还在内测，没有正式 appid/secret
- `moderation` —— 阿里云 Green 尚未接入（见上面的 NotImplementedError）

小程序转正式后，把 `WX_APPID`/`WX_SECRET` 填进 `/etc/venus-4s/.env`（**不能写进
`prod.baseline.env`，那个文件会被烤进镜像推到 ACR**），并从 `ALLOW_MOCK` 去掉 `wechat`。

### 部署前预检（配置不对就不动线上）

自检除了在启动时跑，也能单独当命令用。**在滚容器之前先跑一次**，
它用一个临时容器验证配置，不影响正在跑的服务：

```bash
# 线上
docker compose -f infra/docker-compose.ecs.yml run --rm api python -m app.core.preflight
# 本地
cd apps/api && poetry run python -m app.core.preflight
```

输出会列出当前哪些子系统在 mock、各自的后果，以及占位符没替换等硬错误
（`your-domain.com`、`JWT_SECRET` 还是模板串、`LLM_SYNC_BASE_URL` 为空等）。
返回 0 才代表这份配置能起来。

## 本地开发

后端 `config.py` 的 `env_file` 已指向本文件夹的 `dev.env`（绝对路径，脚本从任何目录启动都能读到）。
改本地配置只需编辑 `config/dev.env`。

小程序端的域名不在这里，走 Taro 自己的 dotenv：`apps/miniapp/.env.development`
（`http://localhost:8080`）与 `.env.production`（`https://rernaco.com`）。
只有 `TARO_APP_` 前缀的变量会被注入客户端，且**明文出现在小程序包里，不要放密钥**。

## 生产部署

1. 非敏感项改 `prod.baseline.env` → 重新 `infra/build.sh` 打镜像。
2. 密钥放服务器 `/etc/venus-4s/.env`（参考 `prod.secrets.example`），`chmod 600`，绝不入镜像。

`infra/build.sh` 会在构建前扫一遍 `prod.baseline.env`，发现 `DATABASE_URL`、`JWT_SECRET`、
`PHONE_DEK_BASE64`、`ALI_ACCESS_KEY_SECRET`、`ADMIN_TOKEN`、`WX_SECRET` 等密钥就直接中止构建。

## 容易配错的项

### `CORS_ORIGINS` —— 默认留空，且大多数情况不该动

逗号分隔的完整 origin（含协议与端口）。**留空 = 后端完全不挂 CORS 中间件**。

| 场景 | 该填什么 |
|------|----------|
| 默认部署（前端与 API 同域，Nginx 反代 `/api`） | **留空**。本就同源，没有跨域，不要无谓放开 |
| 本地开发 | **留空**。前端 devServer 已代理 `/api` 到 8080，浏览器看到的是同源 |
| H5 挂独立域名（如走 CDN） | `https://h5.your-domain.com` |
| 绕过代理、直接用别的端口调 8080 调试 | `http://localhost:10086,http://localhost:5173` |

**微信小程序与此项无关**：小程序不受浏览器同源策略约束，它看的是微信后台的
「服务器域名」白名单（request 与 socket 两处都要加）。

改完重启 api 生效。验证是否挂上：

```bash
cd apps/api
poetry run python -c "from app.main import app; print([m.cls.__name__ for m in app.user_middleware])"
# 留空 → ['RequestIdMiddleware']；配了值 → ['CORSMiddleware', 'RequestIdMiddleware']
```

详见 [docs/references/MINIAPP.md](../docs/references/MINIAPP.md) §5。
