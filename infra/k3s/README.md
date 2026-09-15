# 单机 k3s 一键部署脚本 · 使用手册

本目录（`infra/k3s/`）是 [docs/references/DEPLOY_K3S.md](../../docs/references/DEPLOY_K3S.md) 的自动化实现。手动照文档一步步敲要执行 20+ 条命令，脚本压成一条：

```bash
sudo bash infra/k3s/deploy.sh
```

脚本做的事和文档完全对应：装 k3s → 配 ACR 免密 → 建 namespace → 导入 Secret → 部署业务 → 跑数据库迁移 → 部署模型服务 → 建 ClusterIP Service → 配 NetworkPolicy → 验证连通性。

---

## 目录

- [0. 目录结构](#0-目录结构)
- [1. 前置清单](#1-前置清单)
- [2. 配置 deploy.conf（字段逐项说明）](#2-配置-deployconf字段逐项说明)
- [3. 四种使用姿势](#3-四种使用姿势)
- [4. 脚本内部做了什么（7 个阶段）](#4-脚本内部做了什么7-个阶段)
- [5. 完整首次部署示例](#5-完整首次部署示例)
- [6. 日常升级 / 回滚剧本](#6-日常升级--回滚剧本)
- [7. 幂等性与副作用](#7-幂等性与副作用)
- [8. 常见报错定位表](#8-常见报错定位表)
- [9. 手动验证清单](#9-手动验证清单)
- [10. 卸载 / 清理](#10-卸载--清理)

---

## 0. 目录结构

```
infra/k3s/
├── README.md              # 本文档
├── deploy.sh              # 一键部署主脚本
└── deploy.conf.example    # 配置模板（用户复制成 deploy.conf 后填写）
```

**不提交到 git 的**：`deploy.conf`（含 ACR 密码，用 `.gitignore` 忽略）。

---

## 1. 前置清单

跑脚本之前，逐项确认以下事项：

### 1.1 阿里云资源已就绪

- [ ] ECS 实例已开通、能 SSH root 登录；
- [ ] ECS 与 RDS / Redis / OSS 在**同一 VPC、同一可用区**（不同 VPC 拉不通内网）；
- [ ] ECS 已放行安全组：22（SSH）、30080/30443（如果用 NodePort 暴露 web）、443（如果前挂 SLB）；
- [ ] ACR 命名空间（如 `venus`）已建、api / web / llm 三个仓库已建；
- [ ] RDS / Redis 白名单已加入 ECS 内网网段。

### 1.2 镜像已推 ACR

按 [02-部署实施.md §3](../../docs/02-部署实施.md#3-构建并推送镜像) 完成：

```bash
# 本地机器
cp infra/build.conf.example infra/build.conf
vim infra/build.conf                    # 填 ACR 地址 / 命名空间 / tag
bash infra/build.sh --push              # 构建 + 推 api / web 镜像
```

**模型服务镜像**：如果是自己构建，同样推到 ACR；如果是现成公开镜像，`deploy.conf` 里 `LLM_IMAGE` 填完整地址即可。

验证：

```bash
docker manifest inspect registry.cn-hangzhou.aliyuncs.com/venus/api:v1.0.0
docker manifest inspect registry.cn-hangzhou.aliyuncs.com/venus/llm:v1.0.0
```

返回镜像 manifest 说明推送成功。

### 1.3 密钥文件已写好

按 [02-部署实施.md §6](../../docs/02-部署实施.md#6-在-ecs-上配置密钥文件)：

```bash
# 在 ECS 上
sudo mkdir -p /etc/venus-4s
sudo vim /etc/venus-4s/.env                   # 填 DATABASE_URL / REDIS_URL / JWT_SECRET 等
sudo chmod 600 /etc/venus-4s/.env
```

**要点**：脚本会把这个文件**整个**导入成 `api-secret`，所以文件里放的应该都是敏感项，不要塞公开配置（公开配置放 ConfigMap `01-configmap.yaml`）。

### 1.4 项目文件已上传到 ECS

```bash
# 本地机器
scp -r infra root@<ECS-IP>:/srv/venus-4s/
```

上传后 ECS 上应该有：

```
/srv/venus-4s/infra/k3s/                 # 本目录
/srv/venus-4s/infra/k8s/                 # 业务 Deployment / Service yaml（脚本会用到）
```

---

## 2. 配置 deploy.conf（字段逐项说明）

```bash
cd /srv/venus-4s/infra/k3s
cp deploy.conf.example deploy.conf
chmod 600 deploy.conf                    # 含 ACR 密码，锁死权限
vim deploy.conf
```

### 2.1 ACR 镜像仓库（必填）

| 字段 | 来源 | 示例 |
|---|---|---|
| `ACR_REGISTRY` | ACR 控制台 → 实例 → 访问凭证 → 公网地址 | `registry.cn-hangzhou.aliyuncs.com` |
| `ACR_REGISTRY_VPC` | 同上 → VPC 地址 | `registry-vpc.cn-hangzhou.aliyuncs.com` |
| `ACR_NAMESPACE` | 你在 ACR 建的命名空间名 | `venus` |
| `ACR_USERNAME` | ACR 访问凭证 → 用户名（形如 `<name>@<UID>`） | `ops@1234567890123456` |
| `ACR_PASSWORD` | ACR 访问凭证 → 固定密码（或临时密码） | `<16 位随机串>` |

**为什么要 VPC 地址**：ECS 拉镜像走 `registry-vpc.*` 是**免费**内网流量；走公网地址 `registry.*` 会计费。脚本会把公网地址 mirror 到 VPC 地址，业务侧的 yaml 不用改。

### 2.2 业务镜像 tag（必填）

```
IMAGE_TAG="v1.0.0"
```

与 `infra/build.sh --tag=v1.0.0 --push` 保持一致。**不要用 `latest`**，会失去回滚能力。

### 2.3 模型服务（必填）

| 字段 | 说明 | 示例 |
|---|---|---|
| `LLM_IMAGE` | 完整镜像地址 | `registry.cn-hangzhou.aliyuncs.com/venus/llm:v1.0.0` |
| `LLM_PORT` | 模型服务监听端口 | `8080` |
| `LLM_HEALTH_PATH` | 健康检查路径 | `/health`（服务未实现健康检查的话改成 `/`） |
| `LLM_CPU_REQUEST` / `LLM_CPU_LIMIT` | CPU 需求 / 上限 | `1000m` / `4000m` |
| `LLM_MEM_REQUEST` / `LLM_MEM_LIMIT` | 内存需求 / 上限 | `4Gi` / `8Gi` |
| `LLM_GPU_COUNT` | GPU 数（0=不用 GPU） | `0` |

**GPU 场景注意**：`LLM_GPU_COUNT>0` 要求 ECS 已装 nvidia-container-toolkit 且 k3s 已切成 nvidia runtime。本脚本**不管**这一步，请先按 [k3s 官方 GPU 文档](https://docs.k3s.io/advanced#nvidia-container-runtime-support) 手动配好。

### 2.4 业务密钥文件路径

```
APP_ENV_FILE="/etc/venus-4s/.env"
```

一般不改。脚本会用 `--from-env-file=$APP_ENV_FILE` 把整份文件导入成 `venus-prod/api-secret`。

### 2.5 数据库迁移开关

```
RUN_MIGRATION="true"       # 首次部署 / 发布含新迁移时开
RUN_MIGRATION="false"      # 日常升级（无 schema 变更）关掉，加快部署
```

### 2.6 Web 对外暴露方式

```
WEB_EXPOSE="nodeport"      # 通过 ECS 30080/30443 端口暴露 web（推荐）
WEB_EXPOSE="skip"          # 什么都不动，你自己后面配 Ingress
WEB_NODEPORT_HTTP="30080"
WEB_NODEPORT_HTTPS="30443"
```

**nodeport 模式**：

- 用户访问路径：`用户 → SLB (443) → ECS:30443 → web Pod → nginx (443)`；
- 或直连：`用户 → ECS 公网 IP:30443 → web Pod`（安全组开放 30443）；
- TLS 证书由 web 容器里的 nginx 加载（跟 Docker Compose 方案一致），路径挂载见 `infra/nginx/edge.conf`。

**要用真正的 Ingress**：`WEB_EXPOSE=skip`，然后手动装 ingress-nginx 或 Traefik，参考 [DEPLOY_K3S.md §5.1](../../docs/references/DEPLOY_K3S.md#51-把-kustomization-里的-ingress-换成单机版)。

### 2.7 NetworkPolicy 开关

```
ENABLE_NETWORKPOLICY="true"     # 只允许 venus-prod/api 访问 llm-service，其他 Pod 拒绝
ENABLE_NETWORKPOLICY="false"    # 不启用（如需先联调）
```

**建议**：先用 `false` 跑通，联调 OK 后改 `true` 加隔离。

---

## 3. 四种使用姿势

### 3.1 完整部署（首次）

```bash
sudo bash deploy.sh
```

会跑完 7 个阶段：装 k3s → ACR 配置 → namespace → Secret → 部署业务 → 迁移 → 部署模型 → 验证。

### 3.2 跳过 k3s 安装（k3s 已装过）

```bash
sudo bash deploy.sh --skip-install
```

用于：k3s 装完后又改了配置，想重新部署。会跳过阶段 1，直接从阶段 2 开始。

### 3.3 只重新部署应用（日常发布）

```bash
sudo bash deploy.sh --only-apps
```

跳过：k3s 安装、ACR 配置、Secret 重导（`api-secret` 保留原值）。**日常升级镜像 tag 用这个最合适**。

### 3.4 演练模式（先看一眼要干啥）

```bash
sudo bash deploy.sh --dry-run
```

只打印将执行的命令，不真正执行。生产环境操作前**强烈建议**先跑一次 dry-run。

---

## 4. 脚本内部做了什么（7 个阶段）

对着屏幕输出的 `==> 阶段 X/7` 可以对号入座。

### 阶段 1：安装 k3s

- 检查 `k3s` 命令是否已存在，存在就跳过；
- 走国内镜像加速（`rancher-mirror.rancher.cn`），一条命令装完；
- 参数：`--disable=traefik`（关掉自带 Traefik，用 web 容器里的 nginx）+ `--write-kubeconfig-mode=644`（让非 root 也能读 kubeconfig）；
- 等待 API server 就绪（最多 60 秒）。

**副作用**：ECS 上会新增 systemd 服务 `k3s.service`，数据存 `/var/lib/rancher/k3s/`。

### 阶段 2：配置 ACR 免密拉取

- 写 `/etc/rancher/k3s/registries.yaml`，把公网 ACR 地址 mirror 到 VPC 地址 + 配鉴权；
- 已配过（能在文件里找到 `ACR_REGISTRY_VPC` 字符串）就跳过；
- 新写入的话 `systemctl restart k3s`，再等 API server 就绪。

**副作用**：文件权限设为 600（防其他用户读到密码）。

### 阶段 3：建 namespace

创建 `venus-prod`（业务）+ `llm-prod`（模型服务）两个 namespace。已存在则跳过。

### 阶段 4：导入 Secret

- 业务：`kubectl create secret generic api-secret --from-env-file=$APP_ENV_FILE`（每次都 apply，保证与 `/etc/venus-4s/.env` 同步）；
- 模型：
  - 如果 `llm-prod/llm-secret` 已存在，**复用**其中的 `SERVICE_API_KEY`（避免每次跑脚本都换 key）；
  - 不存在则用 `openssl rand -hex 32` 生成一个 64 位随机 key；
- 同一个 `SERVICE_API_KEY` 会被 patch 到 `venus-prod/api-secret` 的 `LLM_SERVICE_API_KEY` 字段，业务代码读这个 env 去调模型。

### 阶段 5：部署业务

- apply `infra/k8s/01-configmap.yaml`；
- 逐个 apply `10-api-deployment.yaml`、`11-api-service.yaml`、`12-api-hpa.yaml`、`20-web-deployment.yaml`、`21-web-service.yaml`、`30-cron-deployment.yaml`，用 `sed` 替换 `REPLACE_ME_SHA` 为 `IMAGE_TAG`；
- 如果 `WEB_EXPOSE=nodeport`，patch web Service 类型为 NodePort 并暴露 30080/30443。

### 阶段 6：数据库迁移（可选）

- `RUN_MIGRATION=true` 时提交一个 Job：镜像用 `$API_IMAGE`，命令 `alembic upgrade head`，注入 api-secret；
- Job 名字带 timestamp（`migrate-<ts>`）保证唯一，`ttlSecondsAfterFinished: 3600` 让 k8s 一小时后自动清；
- 等 Job 完成（最多 5 分钟），失败会打印日志并退出脚本。

### 阶段 7：部署模型服务

- 用 heredoc 生成 Deployment + Service 的 yaml（按 `deploy.conf` 里的 LLM_* 变量填充），apply；
- 关键设定：`strategy: Recreate`（模型 Pod 通常吃显存，滚动升级新旧共存会 OOM）、`initialDelaySeconds: 120`（模型加载慢，给足时间）；
- 如果 `ENABLE_NETWORKPOLICY=true`，再 apply 一条 NetworkPolicy：只放行 `venus-prod` 命名空间下 `app=api` label 的 Pod。

**收尾**：等三个 Deployment rollout 完成 + 从 api Pod curl 模型健康检查，成功打 OK，失败给出定位提示。

---

## 5. 完整首次部署示例

从零到跑通，全过程 15~30 分钟（模型镜像大的话久一点）。

```bash
# 在本地机器：构建镜像
cp infra/build.conf.example infra/build.conf
vim infra/build.conf                   # ACR_REGISTRY / ACR_NAMESPACE / IMAGE_TAG
bash infra/build.sh --push             # 15 分钟左右

# 上传到 ECS
scp -r infra root@<ECS-IP>:/srv/venus-4s/

# SSH 到 ECS
ssh root@<ECS-IP>

# 在 ECS 上：准备密钥
mkdir -p /etc/venus-4s
vim /etc/venus-4s/.env                 # 参考 02-部署实施.md §6
chmod 600 /etc/venus-4s/.env

# 在 ECS 上：填部署配置
cd /srv/venus-4s/infra/k3s
cp deploy.conf.example deploy.conf
vim deploy.conf                        # 填 ACR 凭证 / LLM_IMAGE 等
chmod 600 deploy.conf

# 先 dry-run 看一眼
sudo bash deploy.sh --dry-run

# 正式部署
sudo bash deploy.sh
```

预期最后输出：

```
✓ 业务 → 模型服务连通性 OK
✓ 部署完成 - 汇总
NAMESPACE     NAME                    READY   STATUS    RESTARTS   AGE
venus-prod    api-7c9d8b7f9d-abcde    1/1     Running   0          1m
venus-prod    api-7c9d8b7f9d-fghij    1/1     Running   0          1m
venus-prod    web-6b5f4c3d2e-klmno    1/1     Running   0          1m
venus-prod    cron-8a7b6c5d4e-pqrst   1/1     Running   0          1m
llm-prod      llm-service-...         1/1     Running   0          1m
```

浏览器打开 `http://<ECS 公网 IP>:30080/health`，返回 `{"status":"ok"}` 表示业务链路通。

---

## 6. 日常升级 / 回滚剧本

### 6.1 升级业务镜像（不动模型服务）

```bash
# 1. 本地构建新版并推 ACR
bash infra/build.sh --tag=v1.1.0 --push

# 2. ECS 上改 tag
cd /srv/venus-4s/infra/k3s
vim deploy.conf                       # IMAGE_TAG="v1.1.0"

# 3. 是否含数据库迁移？
#    含 → RUN_MIGRATION="true"
#    否 → RUN_MIGRATION="false"（快）

# 4. 只重跑应用部分
sudo bash deploy.sh --only-apps
```

### 6.2 升级模型服务镜像

```bash
vim deploy.conf                       # LLM_IMAGE="registry.cn-hangzhou.aliyuncs.com/venus/llm:v2.0.0"
sudo bash deploy.sh --only-apps
```

### 6.3 回滚业务（不用改 conf）

```bash
# 一键回上一版
kubectl -n venus-prod rollout undo deploy/api
kubectl -n venus-prod rollout undo deploy/web

# 或者回到具体版本
kubectl -n venus-prod rollout history deploy/api
kubectl -n venus-prod rollout undo deploy/api --to-revision=3
```

**Alembic 迁移不会自动回滚**，破坏性迁移（删列、改类型）请前向兼容设计（先加新列，双写，再删旧列，分多次发布）。

### 6.4 只重新导入密钥（改了 `/etc/venus-4s/.env` 后）

```bash
# 全量重跑 --only-apps 即可，Secret 会重新 apply
sudo bash deploy.sh --only-apps

# api Pod 需要重启才能拿到新 env
kubectl -n venus-prod rollout restart deploy/api
```

---

## 7. 幂等性与副作用

**幂等**：脚本设计为可以反复执行，同一份 `deploy.conf` 跑多少次结果一致。

**关键的"复用而不是覆盖"逻辑**：

- `llm-prod/llm-secret` 里的 `SERVICE_API_KEY` 首次生成后**不会**被重新生成（否则每次跑脚本都换 key，业务侧配置就跟不上了）；
- 业务侧 `api-secret` **每次都会重新 apply**，因为它可能反映 `/etc/venus-4s/.env` 的最新内容——如果不想动，用 `--only-apps` 之外的手动流程；
- `registries.yaml` 已配则不重复写、不重启 k3s。

**副作用清单**（脚本运行会影响到的宿主机资源）：

| 位置 | 内容 | 备注 |
|---|---|---|
| `/usr/local/bin/k3s` | k3s 二进制 | 卸载：`/usr/local/bin/k3s-uninstall.sh` |
| `/etc/systemd/system/k3s.service` | systemd 单元 | 同上 |
| `/etc/rancher/k3s/registries.yaml` | ACR 免密配置（含明文密码） | chmod 600 |
| `/etc/rancher/k3s/k3s.yaml` | kubeconfig | 644，同机 kubectl 直接用 |
| `/var/lib/rancher/k3s/` | k3s 数据目录（etcd/SQLite + 镜像缓存 + 容器 rootfs） | 可能占几 GB~几十 GB |

---

## 8. 常见报错定位表

| 报错 / 现象 | 阶段 | 原因 | 解决 |
|---|---|---|---|
| `curl: (28) Connection timed out` 拉 k3s 安装脚本 | 1 | ECS 出不了公网 | 给 ECS 绑弹性公网 IP，或走内网 SNAT |
| `Error from server: no matches for kind "Namespace"` | 3 | k3s API server 还没就绪 | 等 30 秒重试；或看 `journalctl -u k3s` |
| `pull access denied` / `unauthorized` | 5/7 | ACR 用户名密码错，或 namespace 权限不对 | 检查 `ACR_USERNAME` 是否是 `<name>@<UID>` 格式；ACR 控制台重置固定密码 |
| `ImagePullBackOff` | 5/7 | 镜像 tag 不存在，或 registries.yaml 没生效 | `docker manifest inspect ...` 验证 tag；确认 `systemctl restart k3s` 后 registries.yaml 生效 |
| Job `migrate-xxx` 一直 pending | 6 | 节点资源不够 / imagePullBackOff | `kubectl -n venus-prod describe job/migrate-xxx` |
| Job 失败：`Access denied for user` | 6 | `DATABASE_URL` 密码错或未 URL 编码 | 改 `/etc/venus-4s/.env` 后 `--only-apps` 重跑 |
| Job 失败：`Can't connect to MySQL server` | 6 | RDS 白名单没加 ECS 内网 IP，或不同 VPC | 阿里云控制台 → RDS → 白名单 |
| llm-service Pod 频繁重启 | 7 | 内存不够被 OOMKilled，或 readinessProbe 一直失败 | `kubectl -n llm-prod describe pod ...` 看 Reason；调大 `LLM_MEM_LIMIT`；把 `LLM_HEALTH_PATH` 改成实际存在的 200 路径 |
| `业务 → 模型服务连通性 检查失败` | 收尾 | 模型加载慢 / 健康检查路径错 / NetworkPolicy 拦了 | 等 3~5 分钟再测；对齐 `LLM_HEALTH_PATH`；临时 `ENABLE_NETWORKPOLICY=false` 排除 |
| `nslookup` 解析不到 `*.svc.cluster.local` | 收尾 | CoreDNS 挂了 | `kubectl -n kube-system get pods` 看 coredns |

---

## 9. 手动验证清单

脚本自带的连通性检查过了不代表业务真的能用。上线前手动跑一遍：

```bash
# 1. 所有 Pod 都 Running
kubectl get pods -A | grep -Ev 'Running|Completed'
# 预期：只有表头，没有其他行

# 2. 业务 → 模型
kubectl -n venus-prod exec deploy/api -- \
    curl -sf http://llm-service.llm-prod.svc.cluster.local:8080/health

# 3. 业务 → RDS
kubectl -n venus-prod exec deploy/api -- \
    python -c "from app.db import ping; import asyncio; asyncio.run(ping())"

# 4. 业务 → Redis
kubectl -n venus-prod exec deploy/api -- \
    python -c "from app.redis import ping; import asyncio; asyncio.run(ping())"

# 5. 业务健康检查
kubectl -n venus-prod exec deploy/api -- curl -sf localhost:8000/health

# 6. 从 ECS 外部访问 web
curl -k https://<ECS 公网 IP>:30443/health          # NodePort 模式
# 或
curl -k https://<你的域名>/health                    # 域名解析已配好

# 7. 冒烟测试
HOST=https://<你的域名> bash scripts/smoke.sh
```

全绿再对外放量。

---

## 10. 卸载 / 清理

**只删业务和模型，保留 k3s**：

```bash
kubectl delete namespace venus-prod llm-prod
```

**彻底卸载 k3s**（会删所有 Pod、镜像缓存、k8s 元数据；**不会**动 RDS/OSS/ACR）：

```bash
/usr/local/bin/k3s-uninstall.sh
```

**清理 ACR 免密配置**（含明文密码）：

```bash
sudo rm /etc/rancher/k3s/registries.yaml
```

---

## 参考

- 完整背景 / 架构 / 原理：[docs/references/DEPLOY_K3S.md](../../docs/references/DEPLOY_K3S.md)
- Docker Compose 部署方案：[docs/02-部署实施.md](../../docs/02-部署实施.md)
- ACK 托管 K8s 方案：[docs/references/DEPLOY_K8S.md](../../docs/references/DEPLOY_K8S.md)
- 日常运维：[docs/04-日常运维与排查.md](../../docs/04-日常运维与排查.md)
