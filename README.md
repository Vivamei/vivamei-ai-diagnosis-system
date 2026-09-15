# venus-4s · 薇分美学 4S H5

医美 AI 4S 美学诊断应用 (5万版 v3.0)。前端两个产物：H5（React + Vite）与微信小程序（Taro），共用同一套后端 FastAPI + MySQL + Redis，模型层对接 LLM 服务。

## 快速开始（本地开发）

**Windows**：双击 `start-dev.bat`，一步到位——检查工具链、从模板生成 `config/dev.env`、装后端 venv 与 H5 前端依赖、起 MySQL/Redis + 迁移 + API(8080) + Web(5173)。首次 5-15 分钟，之后几秒。要开发小程序端，另在仓库根跑一次 `pnpm install` 装齐 workspace 全部包。

**其他平台**：`make install` 装依赖，`make dev` 起依赖服务。

手动等价命令：

```bash
make install                                  # 装依赖（apps/api venv + pnpm workspace 全部包）
make dev                                      # 起 dev 依赖 (mysql / redis)
cd apps/api && poetry run alembic upgrade head && poetry run uvicorn app.main:app --reload --port 8080
cd apps/web && pnpm dev                       # H5
pnpm --filter @venus/miniapp dev:weapp        # 小程序（产物用微信开发者工具打开 apps/miniapp/dist）
```

Windows 双击启动请看 [docs/双击启动.md](docs/双击启动.md)；不用 Docker 起本地环境请看 [docs/references/LOCAL_DEV_NO_DOCKER.md](docs/references/LOCAL_DEV_NO_DOCKER.md)；小程序双端开发看 [docs/references/MINIAPP.md](docs/references/MINIAPP.md)。

---

## 文档索引

### 阿里云部署主线（按顺序阅读）

生产部署按 01→02→03→04 顺序推进，任何一步卡住都别跳。

| 编号 | 文档 | 内容 |
|---|---|---|
| 01 | [docs/01-部署前准备.md](docs/01-部署前准备.md) | 开通阿里云资源（ECS/RDS/KVStore/OSS/ACR/RAM/短信/内容审核）、办域名 ICP 备案、申请 SSL 证书、生成密钥、汇总连接信息 |
| 02 | [docs/02-部署实施.md](docs/02-部署实施.md) | 本地构建镜像 → 推 ACR → ECS 装 Docker → 拉镜像 → 建库 → 起容器（Docker Compose 方案） |
| 03 | [docs/03-部署验证.md](docs/03-部署验证.md) | 从公网视角完整验证：DNS、证书、健康检查、端到端业务链路 |
| 04 | [docs/04-日常运维与排查.md](docs/04-日常运维与排查.md) | 发布 / 回滚 / 备份 / 扩容 / 迁移 / 故障排查 / 性能监控 / 安全事件响应 |
| — | [docs/00-资源申请清单.md](docs/00-资源申请清单.md) | 项目立项阶段用的资源与预算清单 |
| — | [docs/README.md](docs/README.md) | docs 目录的完整索引 |

### 三种部署方案对比

| 方案 | 适用场景 | 文档 | 一键脚本 |
|---|---|---|---|
| **Docker Compose**（默认） | 单机、无模型服务、MVP、月 PV < 10w | [docs/02-部署实施.md](docs/02-部署实施.md) | [infra/build.sh](infra/build.sh) 打镜像 + `docker compose up -d` |
| **单机 k3s**（推荐用于同机部署业务+模型） | 一台 ECS 同时跑业务和模型 Pod，用 ClusterIP Service 打通 | [docs/references/DEPLOY_K3S.md](docs/references/DEPLOY_K3S.md) | [infra/k3s/deploy.sh](infra/k3s/deploy.sh) 一键部署（[使用手册](infra/k3s/README.md)） |
| **阿里云 ACK 托管** | 多机弹性伸缩、跨机房容灾、CI/CD 滚动发布 | [docs/references/DEPLOY_K8S.md](docs/references/DEPLOY_K8S.md) | 见文档 §5（`kubectl apply -k infra/k8s/`） |

> **怎么选？** MVP 阶段用 Compose；需要跑本地模型或 Service DNS 用单机 k3s；月活破万、需高可用用 ACK。详细取舍见 [DEPLOY_K3S.md §12](docs/references/DEPLOY_K3S.md#12-与-docker-compose-方案的取舍)。

### 生产上线全流程（k3s 单机方案）

从 push ACR 到 Pod 在 ECS 上跑起来的浓缩流程。适用场景：一台 ECS 同时跑业务 Pod 和模型服务 Pod。**步骤 2~10 由 [`infra/k3s/deploy.sh`](infra/k3s/deploy.sh) 一键完成**，你只需要做步骤 1、填两个配置文件。

**先看清三个文档的分工**（避免找错地方）：

| 文档 | 什么时候看 |
|---|---|
| **本 README** | 了解全局 / 找入口 / 看端到端命令 |
| [infra/k3s/README.md](infra/k3s/README.md) | 快速执行 → 脚本用法、`deploy.conf` 字段说明、常见报错定位表 |
| [docs/references/DEPLOY_K3S.md](docs/references/DEPLOY_K3S.md) | 理解原理 / 手动排查 / 定制脚本未覆盖的场景 |

**10 步全景**：

| # | 做什么 | 由谁执行 | 详情 |
|---|---|---|---|
| 1 | 本机打镜像 + 推 ACR（api + web 两个镜像） | 手动 `bash infra/build.sh --push` | ↓ 下面「打镜像 & 推 ACR」 |
| 2 | ECS 上装 k3s（走国内镜像加速） | `deploy.sh` 阶段 1 | [DEPLOY_K3S.md §2](docs/references/DEPLOY_K3S.md#2-在-ecs-上安装-k3s) |
| 3 | 配 ACR 免密拉取（VPC 内网免流量费） | `deploy.sh` 阶段 2 | [DEPLOY_K3S.md §3](docs/references/DEPLOY_K3S.md#3-让-k3s-能拉-acr-私有镜像) |
| 4 | 建 namespace `venus-prod` / `llm-prod` | `deploy.sh` 阶段 3 | [DEPLOY_K3S.md §4](docs/references/DEPLOY_K3S.md#4-建命名空间) |
| 5 | 导入业务 Secret（从 `/etc/venus-4s/.env`）+ 生成模型 `SERVICE_API_KEY` | `deploy.sh` 阶段 4 | [DEPLOY_K3S.md §5.2](docs/references/DEPLOY_K3S.md#52-建-configmap--secret) |
| 6 | 部署业务 Pod（api + web + cron + ConfigMap + HPA），复用 `infra/k8s/` | `deploy.sh` 阶段 5 | [DEPLOY_K3S.md §5](docs/references/DEPLOY_K3S.md#5-部署业务-pod复用-infrak8s) |
| 7 | 执行 Alembic 数据库迁移（首次或含新迁移时） | `deploy.sh` 阶段 6 | [DEPLOY_K3S.md §9 步骤 6](docs/references/DEPLOY_K3S.md#9-完整部署清单首次上线) |
| 8 | 部署模型服务 Pod + ClusterIP Service，业务通过 `http://llm-service.llm-prod.svc.cluster.local:8080` 访问 | `deploy.sh` 阶段 7 | [DEPLOY_K3S.md §6](docs/references/DEPLOY_K3S.md#6-部署模型服务-pod) / [§7](docs/references/DEPLOY_K3S.md#7-建-clusterip-service业务--模型) |
| 9 | NetworkPolicy 隔离：只允许 `venus-prod/api` 访问模型服务 | `deploy.sh` 阶段 7 | [DEPLOY_K3S.md §8](docs/references/DEPLOY_K3S.md#8-用-networkpolicy-限制访问可选但推荐) |
| 10 | 收尾：从业务 Pod curl 模型健康检查，打印所有 Pod / Service 状态 | `deploy.sh` 收尾 | [DEPLOY_K3S.md §7.3](docs/references/DEPLOY_K3S.md#73-验证服务连通性) |

#### 你实际要敲的命令（首次全量部署）

```bash
# ========== 本机 ==========
docker login registry.cn-hangzhou.aliyuncs.com    # 生涯就一次（Windows Desktop 详见下面「打镜像 & 推 ACR」）
bash infra/build.sh --push                        # 打两个镜像 + 推 ACR

# 项目上传到 ECS
scp -r infra root@<ECS-IP>:/srv/venus-4s/

# ========== ECS 上 ==========
ssh root@<ECS-IP>

# 一次性：写业务密钥（详见 docs/02-部署实施.md §6）
mkdir -p /etc/venus-4s
vim /etc/venus-4s/.env
chmod 600 /etc/venus-4s/.env

# 一次性：填 k3s 部署配置
cd /srv/venus-4s/infra/k3s
cp deploy.conf.example deploy.conf
vim deploy.conf                      # ACR 凭证 / IMAGE_TAG / LLM_IMAGE 等（字段详解见 infra/k3s/README.md §2）
chmod 600 deploy.conf

# 一键部署（做完 10 步中的 2~10）
sudo bash deploy.sh --dry-run        # 先演练，看脚本会干啥
sudo bash deploy.sh                  # 正式跑
```

#### 日常发布（不装 k3s、不动 ACR 配置，只换镜像 tag）

```bash
# 本机
bash infra/build.sh --tag=v1.1.0 --push

# ECS
vim /srv/venus-4s/infra/k3s/deploy.conf     # IMAGE_TAG=v1.1.0
sudo bash /srv/venus-4s/infra/k3s/deploy.sh --only-apps
```

**回滚**：`kubectl -n venus-prod rollout undo deploy/api`（详见 [infra/k3s/README.md §6](infra/k3s/README.md#6-日常升级--回滚剧本)）。

### 打镜像 & 推 ACR（`infra/build.sh`）

三种方案都依赖同一个打包脚本：[`infra/build.sh`](infra/build.sh) 会构建 **api + web 两个镜像**（前后端分离，不合并成单镜像），并可选推送到阿里云 ACR。

> **第一次用 ACR？** 从注册实例、建命名空间/仓库到 `docker login` + 推镜像的完整教程见 [docs/references/ACR_GUIDE.md](docs/references/ACR_GUIDE.md)（含常见报错定位表）。

**准备**：

```bash
cp infra/build.conf.example infra/build.conf
vim infra/build.conf              # 填 ACR_REGISTRY / ACR_NAMESPACE / IMAGE_TAG / PLATFORM
```

#### 如何登录 ACR（首次一次即可）

阿里云 ACR **没有像 GitHub 那样的浏览器 OAuth 登录**，只能用「用户名 + 密码」走 Docker Registry 标准协议登录。**好消息是首次登录后 Docker 会把凭证缓存到 `~/.docker/config.json`，本机之后所有 `docker push` / `bash infra/build.sh --push` 都自动免密**——效果等同于 `gh auth login` 后 `git push` 免密的体验，只是首次那一下没有浏览器。

**第一步：拿到 ACR 账号密码**

1. 登录阿里云控制台 → 容器镜像服务 ACR → 选实例 → 左侧「访问凭证」
2. 页面上会看到：
   - **用户名**：形如 `ops@1234567890123456`（@ 前是你的 RAM 用户名，@ 后是主账号 UID）
   - **密码**：分「固定密码」和「临时密码」
     - **固定密码**：首次点击「设置固定密码」后自定义，长期有效
     - **临时密码**：控制台点击「获取临时 token」生成，约 1 小时过期，只适合一次性使用

**推荐：使用固定密码**——设一次终身不用管，本机免密体验最好。

**第二步：手动 docker login（等效脚本自动做的事）**

```bash
docker login registry.cn-hangzhou.aliyuncs.com
# Username: ops@1234567890123456     ← 输入 ACR 用户名
# Password: ****                      ← 输入 ACR 密码（不会回显）
# Login Succeeded                     ← 看到这个就成功
```

之后**不用再登录**——凭证已经缓存到 `~/.docker/config.json`。跑 `bash infra/build.sh --push` 时脚本会检测缓存并跳过 login。

**如果你**要**换 registry 地区/换账号 → 重新 login 会覆盖旧凭证**。凭证过期时（例如临时密码用完了）加 `--relogin` 强制重登。

**第三步：地区选择**

如果你在 ECS 上打镜像/推镜像，用 VPC 内网地址免流量费：

```bash
docker login registry-vpc.cn-hangzhou.aliyuncs.com    # ECS 内推 ACR 用这个
docker login registry.cn-hangzhou.aliyuncs.com        # 本机开发用这个
```

（两个地址是两套独立凭证，需要**分别 login 一次**。）

#### Windows + Docker Desktop 用户快速操作

**在哪里执行 `docker login`**：任何能跑 `docker` 的终端都行（Docker Desktop 装完后自动把 `docker` 加到 PATH）。三选一：

| 终端 | 打开方式 | 备注 |
|---|---|---|
| **Git Bash**（推荐） | 在项目文件夹右键 → "Open Git Bash Here" | 命令直接复制粘贴即可用，路径分隔符统一 `/` |
| **PowerShell / Windows Terminal** | `Win + X` → Windows PowerShell / Terminal | 命令一样能跑 |
| **WSL 里的终端** | 打开 Ubuntu 等 | 需要在 Docker Desktop → Settings → Resources → WSL Integration 开启对应发行版 |

**能不能在 Docker Desktop 的 GUI 里绑定 ACR**：**不能**。Docker Desktop 右上角的 "Sign in" 按钮**只支持 Docker Hub 账号**，不支持任何第三方 registry（ACR / GCR / GHCR / Harbor 等）。这是 Docker 官方的产品设计，跟阿里云无关。

**但**：一旦你在命令行 `docker login` 成功，Docker Desktop **会自动识别**这个凭证——之后在 Desktop GUI 里查看 Images 列表、pull 私有镜像等操作都会自动带上认证，密码由 Windows 凭据管理器（DPAPI 加密）保管。

**完整实操**（复制粘贴即可）：

```bash
# 1. 在项目根目录右键 → Git Bash Here，或开 PowerShell

# 2. 登录 ACR（此步骤生涯就做一次）
docker login registry.cn-hangzhou.aliyuncs.com
# Username: ops@1234567890123456   ← 输 ACR 用户名（阿里云控制台 → 容器镜像服务 → 实例 → 访问凭证）
# Password: ****                    ← 输 ACR 固定密码，不回显
# Login Succeeded                   ← 看到这行就是成功了

# 3. 之后所有推送都自动免密（终身有效，除非手动 docker logout 或换机器）
cd C:/work/md_file/weixin/yimei-rfp/yimei-4s
bash infra/build.sh --push
# → 脚本自动检测缓存："✓ registry.cn-hangzhou.aliyuncs.com 已有本地凭证缓存，跳过 docker login"
# → 直接开始打镜像 + 推 ACR
```

**验证 login 是否真的进了加密存储**：

1. 命令行输出 `Login Succeeded` ✅
2. `cat ~/.docker/config.json` 里的 `auths` 应该出现类似 `"registry.cn-hangzhou.aliyuncs.com": {}` 的**空对象**（**没有** `"auth": "base64..."` 字段），说明密码不在文件里
3. 按 `Win + R` → 输入 `control /name Microsoft.CredentialManager` → 「Windows 凭据」标签页 → 应能找到 `docker:registry.cn-hangzhou.aliyuncs.com` 条目，密码在此加密存储

**常见问题**：

- **`docker: command not found`** → Docker Desktop 没启动。启动它，等右下角 whale 图标变绿再试
- **`Error saving credentials`** → Windows 凭据管理器服务被关了。`services.msc` 找 "Credential Manager"，设为自动启动
- **想换账号 / 迁移到新的 RAM 子账号** → `docker logout registry.cn-hangzhou.aliyuncs.com` 清掉旧凭证，再 `docker login` 一次
- **推送时 `denied: requested access to the resource is denied`** → 用户名密码正确但当前 RAM 用户没有对应 ACR namespace 的权限。让主账号在 ACR 控制台给你的 RAM 用户加 `cr:PushRepository` 权限

#### 四种推送姿势（按你的自动化程度选）

| 场景 | 命令 | ACR 账号来源 |
|---|---|---|
| 只本地构建，不推 | `bash infra/build.sh` | 不需要 |
| 首次推 ACR | `bash infra/build.sh --push` | 弹出 `docker login` 交互提示，输一次终身缓存 |
| **之后再推**（本机第 2、3、N 次） | `bash infra/build.sh --push` | 脚本自动检测 `~/.docker/config.json` 已缓存，跳过 login |
| 凭证过期需强制重登 | `bash infra/build.sh --push --relogin` | 忽略缓存，重新走 login 逻辑 |
| **零交互推**（CI / 脚本自动化推荐） | `ACR_USERNAME='ops@<UID>' ACR_PASSWORD='xxx' bash infra/build.sh --push` | 从环境变量读，走 `docker login --password-stdin`（不进 shell 历史 / 进程列表） |
| 长期本机常用（不想每次 login） | 把 `ACR_USERNAME` / `ACR_PASSWORD` 填到 `infra/build.conf`（**必须 `chmod 600` + `.gitignore`**），然后 `bash infra/build.sh --push` | 从 build.conf 读 |

**登录逻辑优先级**（脚本内部）：本机凭证缓存 > 环境变量 > `build.conf` > 交互式提示。

#### 指定 tag / 平台

```bash
bash infra/build.sh --tag=v1.2.0 --push                    # 覆盖 build.conf 里的 tag
bash infra/build.sh --platform=linux/arm64                  # 指定架构（Apple Silicon 打 x86 ECS 必须显式指定 linux/amd64）
```

#### 产物

- `<ACR_REGISTRY>/<ACR_NAMESPACE>/api:<TAG>` — FastAPI 后端镜像
- `<ACR_REGISTRY>/<ACR_NAMESPACE>/web:<TAG>` — nginx + Vite 静态产物镜像

推完之后：Compose 方案继续走 [02 §9](docs/02-部署实施.md#9-初始化数据库并启动容器)，k3s 方案继续走 [infra/k3s/README.md](infra/k3s/README.md) 的 `deploy.sh`。

### 本地开发

| 文档 | 说明 |
|---|---|
| [docs/references/LOCAL_DEV.md](docs/references/LOCAL_DEV.md) | 基于 Docker 的本地开发环境（推荐） |
| [docs/references/LOCAL_DEV_NO_DOCKER.md](docs/references/LOCAL_DEV_NO_DOCKER.md) | 不用 Docker 直接跑（Windows 常用） |
| [docs/双击启动.md](docs/双击启动.md) | Windows 双击 `start-dev.bat` 启动 |
| [docs/本地数据库连接指南.md](docs/本地数据库连接指南.md) | 本地连 MySQL/Redis 的连接串与图形化工具配置 |
| [docs/references/LLM_API_ALIGNMENT.md](docs/references/LLM_API_ALIGNMENT.md) | 与 LLM 服务方对齐的接口协议 |

### 设计

| 文档 | 说明 |
|---|---|
| [docs/design/design.md](docs/design/design.md) | 8 段技术设计稿（架构 / DB / API / LLM 契约 / 合规） |
| [docs/design/sections/](docs/design/sections/) | 按章节拆分的设计片段 |

### 基础设施 / 脚本

| 位置 | 内容 |
|---|---|
| [infra/build.sh](infra/build.sh) | 构建 api/web 镜像并推 ACR（读取 `infra/build.conf`） |
| [infra/build.conf.example](infra/build.conf.example) | 构建配置模板（ACR 地址、镜像 tag、target platform） |
| [config/prod.baseline.env](config/prod.baseline.env) | 烤进镜像的非敏感配置（**禁放密钥**） |
| [infra/docker-compose.dev.yml](infra/docker-compose.dev.yml) | 本地 dev 依赖（mysql + redis） |
| [infra/docker-compose.ecs.yml](infra/docker-compose.ecs.yml) | **生产主线**：ECS 上跑 api/web/cron（db 走托管 RDS/KVStore） |
| [infra/nginx/](infra/nginx/) | web 容器内 nginx 配置（`edge.conf` TLS 终止 + 反代 /api；`web.conf` 内层静态） |
| [infra/k8s/](infra/k8s/) | ACK 场景 K8s yaml（Deployment / Service / HPA / Ingress） |
| [infra/k3s/](infra/k3s/) | 单机 k3s 一键部署脚本（推荐同机跑业务+模型时使用） |
| [scripts/backup.sh](scripts/backup.sh) | 数据库备份脚本 |
| [scripts/smoke.sh](scripts/smoke.sh) | 冒烟测试（健康检查 / OpenAPI / 短信限流 / 静态首页） |
| [scripts/export-leads.py](scripts/export-leads.py) | 留资导出 |
| [scripts/init_sensitive_words.py](scripts/init_sensitive_words.py) | 敏感词初始化 |
| [scripts/gen-types.sh](scripts/gen-types.sh) | 从 OpenAPI 生成前端 TS 类型 |
| [scripts/gh-link.sh](scripts/gh-link.sh) | 通用 git 关联助手（本项目不用 git，备用） |
| [scripts/tee.bat](scripts/tee.bat) | 简易 tee（字节级透传，避免日志中文乱码） |
| [scripts/README.md](scripts/README.md) | **所有脚本总目录**（含根目录/infra 下的脚本说明） |

### 外部交接材料

- [docs/操作手册-新建RAM子账号与MySQL-Redis资源.docx](docs/操作手册-新建RAM子账号与MySQL-Redis资源.docx)：可打印分发的资源开通操作手册，内容与 01 §2~§5 一致，便于外部协作人员离线阅读。

---

## 项目结构

> 经过一轮整理，**配置、脚本、文档、Mock 数据各自归口到专属目录**，每个目录都有自己的 `README.md` 说明。

```
yimei-4s/
├── apps/
│   ├── api/                    # FastAPI 后端（app / alembic / tests / Dockerfile）
│   ├── web/                    # React + Vite H5 前端（src / public / Dockerfile）
│   └── miniapp/                # Taro 微信小程序（与 web 共用后端接口，详见 docs/references/MINIAPP.md）
├── packages/
│   └── shared-types/           # 前后端共享 TS 类型（从 OpenAPI 生成）
├── config/                     # 【统一配置】所有 env 配置集中在此
│   ├── dev.env                 #   本地开发运行时配置（active，键清单与后端 Settings 一一对应）
│   ├── dev.env.example         #   本地配置模板
│   ├── frontend.env            #   前端配置唯一真源（H5 + 小程序共用，手写；生成三份 .env）
│   ├── prod.baseline.env       #   烤进镜像的非敏感基线（构建时 COPY 到镜像 /app/.env，禁放密钥）
│   ├── prod.secrets.example    #   生产运行时完整配置样例 → 部署时复制到 /etc/venus-4s/.env 填真实值
│   └── README.md               #   配置分层说明（dev / 基线 / 密钥 的优先级与去向）
├── docs/                       # 【统一文档】部署主线 01~04 + 设计 / 计划 / 参考（详见上表）
├── infra/                      # 基础设施 / 部署配置
│   ├── build.sh                #   打镜像脚本（扫描 prod.baseline.env，发现密钥即终止构建）
│   ├── docker-compose.*.yml    #   dev / ecs / prod 三套 compose
│   ├── nginx/                  #   nginx 配置
│   ├── k8s/                    #   ACK K8s yaml
│   └── k3s/                    #   单机 k3s 一键部署
├── mock/                       # 【Mock 数据】与代码分离
│   ├── sample_report.json      #   mock LLM provider 读取的样例报告
│   └── README.md
├── scripts/                    # 【统一脚本】运维 / 构建 / 导出脚本
│   ├── backup.sh               #   数据库备份
│   ├── smoke.sh                #   冒烟测试
│   ├── export-leads.py         #   留资导出
│   ├── init_sensitive_words.py #   敏感词初始化
│   ├── loadtest_analyze.py     #   报告生成并发压测
│   ├── gen-types.sh            #   OpenAPI → 前端 TS 类型
│   ├── gen-frontend-env.mjs    #   config/frontend.env → web/miniapp 各自的 .env（构建脚本自动调）
│   ├── tee.bat                 #   简易 tee（字节级透传，避免日志中文乱码）
│   └── README.md               #   所有脚本总目录（含根目录 / infra 下脚本）
├── .github/workflows/ci.yml    # CI：后端 lint/test + 前端构建
├── pnpm-workspace.yaml         # pnpm workspace 声明（apps/web、apps/miniapp、packages/*）
├── logs/                       # 运行时日志，start-dev.bat 自动创建（不入库）
├── _local/                     # 本地产物集散地：问题现场截图 / 历史日志 / 待删垃圾（不入库不打包）
├── Makefile
├── start-dev.bat / stop-dev.bat  # Windows 双击启动（含装依赖）/ 停止
├── make-distribution.bat       # 打包免安装分发包
└── README.md                   # 本文件
```

> `logs/`、`apps/api/var/`（本地 OSS 兜底的上传目录）、`_local/` 都是运行时/本地目录，
> 已在 `.gitignore` 与 `.dockerignore` 中排除，不要往里放需要长期保留的东西。

**配置分层一图看懂**（详见 [config/README.md](config/README.md)）：

| 文件 | 去向 | 放什么 | 谁覆盖谁 |
|---|---|---|---|
| `config/dev.env` | 本地进程直接读 | 本地全部配置 | — |
| `config/prod.baseline.env` | 构建时烤进镜像 `/app/.env` | **仅非密钥**（App/OSS/LLM/限流等） | 基线（兜底） |
| `config/prod.secrets.example` | 复制到服务器 `/etc/venus-4s/.env` | **完整清单**：密钥填真值 + 非密钥可覆盖基线 | 运行时 env_file（最高优先级） |

前端配置走另一条链路：`config/frontend.env` 是 H5 与小程序共用的**唯一真源**，构建时由
`scripts/gen-frontend-env.mjs` 拆成 `apps/web/.env.production`（`VITE_*`）与
`apps/miniapp/.env.production` / `.env.development`（`TARO_APP_*`）三个**生成物**——这三个文件不要手改。
只放会进前端包的公开配置（API 基址、小程序 appid、品牌文案），密钥一律不进。详见
[docs/references/MINIAPP.md §10](docs/references/MINIAPP.md)。

---

## 常见入口速查

| 我想... | 去看 |
|---|---|
| **第一次拉代码，把依赖装齐** | 双击 `install-deps.bat`，或 `make install` |
| 本地跑起来 | 上面「快速开始」+ [docs/双击启动.md](docs/双击启动.md) |
| 开发 / 构建微信小程序 | [docs/references/MINIAPP.md](docs/references/MINIAPP.md)（双端差异、配置真源、appid 切换） |
| **从零上线（k3s 单机 · 业务+模型同机）** | 上面「[生产上线全流程](#生产上线全流程k3s-单机方案)」10 步表格 |
| **日常发布新版本**（换镜像 tag） | `bash infra/build.sh --tag=vX.Y --push` → ECS 上 `sudo bash infra/k3s/deploy.sh --only-apps` |
| 部署到生产（最简单，无模型服务） | [docs/02-部署实施.md](docs/02-部署实施.md)（Docker Compose 方案） |
| 部署时业务和模型服务放同一台 ECS | [infra/k3s/README.md](infra/k3s/README.md) → `sudo bash infra/k3s/deploy.sh` |
| 打镜像推 ACR（交互式） | `bash infra/build.sh --push` |
| 打镜像推 ACR（零交互，脚本化） | `ACR_USERNAME=... ACR_PASSWORD=... bash infra/build.sh --push` |
| 出线上故障了排查 | [docs/04-日常运维与排查.md](docs/04-日常运维与排查.md) + [infra/k3s/README.md §8 报错定位表](infra/k3s/README.md#8-常见报错定位表) |
| 理解整体架构与设计 | [docs/design/design.md](docs/design/design.md) |
| 对接 LLM 服务方 | [docs/references/LLM_API_ALIGNMENT.md](docs/references/LLM_API_ALIGNMENT.md) |
