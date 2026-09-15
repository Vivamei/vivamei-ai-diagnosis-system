# 阿里云 K8s 部署手册（ACK 版）

> 这是 K8s 版部署文档。ECS + Docker Compose 版见 [DEPLOY.md](./DEPLOY.md)。
> 适用场景：流量增长、需要弹性伸缩、多实例高可用、滚动发布。

---

## 0. 架构总览

```
                            用户
                              │ HTTPS (公网域名 venus.example.com)
                              ▼
                  ┌───────────────────────┐
                  │  阿里云 DNS (域名解析) │
                  └──────────┬────────────┘
                              │ CNAME / A
                              ▼
                  ┌───────────────────────┐
                  │   SLB / CLB (公网)     │  ← ACK 自动创建
                  └──────────┬────────────┘
                              │
                              ▼
              ┌──────────────────────────────┐
              │  Ingress (nginx-ingress)      │  TLS 终止
              └─────┬─────────────────┬───────┘
                    │  /api/*         │  /  (静态)
                    ▼                 ▼
        ┌─────────────────┐   ┌─────────────────┐
        │ Service: api    │   │ Service: web    │
        │ ClusterIP :8000 │   │ ClusterIP :80   │
        └────────┬────────┘   └────────┬────────┘
                 ▼                     ▼
        ┌─────────────────┐   ┌─────────────────┐
        │ Deployment: api │   │ Deployment: web │
        │ 2 ~ 6 副本(HPA) │   │ 2 副本 (nginx)  │
        └────────┬────────┘   └─────────────────┘
                 │
        ┌────────┴────────────────┐
        │  Deployment: cron       │  1 副本（定时任务 worker）
        └─────────────────────────┘

  数据层（不放 K8s，用云托管）：
  ├─ RDS MySQL 8.0        （DB）
  ├─ 云数据库 Tair / Redis （缓存 / 限流 / 验证码）
  ├─ OSS                  （图片 / 报告导出）
  ├─ 阿里云内容安全        （审核）
  └─ 阿里云短信服务        （登录验证码）

  镜像仓库：ACR (容器镜像服务) — registry.cn-hangzhou.aliyuncs.com/venus/*
```

**为什么数据层不放集群里**：MySQL/Redis 上 K8s 等于自找麻烦（备份、扩容、HA 都要你自己扛），托管服务 RDS/Tair 是默认选择。

---

## 1. 前置准备（一次性）

### 1.1 账号 / 资源开通

| 资源                | 用途                          | 备注                                 |
| ------------------- | ----------------------------- | ------------------------------------ |
| 主账号 + RAM 子账号 | 部署 / 应用 OSS-AK            | 部署用拥有 ACK/ACR/RDS 权限的子账号  |
| 域名                | 业务访问                      | **必须完成 ICP 备案**，未备案 80/443 走不通 |
| ACR 容器镜像服务    | 存镜像                        | 个人版免费够用，企业版可选           |
| ACK 托管版集群      | 跑应用                        | 推荐"专有版集群 ACK Pro"，3 worker 起步 |
| RDS MySQL 8.0       | 业务库                        | 与 ACK 同 VPC + 同可用区             |
| 云数据库 Tair       | Redis 兼容                    | 与 ACK 同 VPC                        |
| OSS                 | 文件存储                      | 同 region，配 STS 临时凭证           |
| 内容安全 / 短信     | 已在代码里集成               | RAM 子账号开权限即可                 |

### 1.2 子账号权限（最小集合）

部署用的 RAM 子账号至少要这些策略：

- `AliyunACRFullAccess`（推 / 拉镜像）
- `AliyunCSFullAccess`（管 ACK）
- `AliyunRDSReadOnlyAccess`（拿连接串就够）
- `AliyunVPCReadOnlyAccess`、`AliyunSLBFullAccess`（Ingress / Service）

应用运行用的子账号（写到 K8s Secret）单独建一个，只给 OSS / 内容安全 / 短信 的权限。

### 1.3 本地工具

```bash
# 装好以下 CLI
aliyun --version          # 阿里云 CLI
kubectl version --client  # K8s CLI
helm version              # Helm（装 ingress-nginx / cert-manager 用）
docker --version

# 从 ACK 控制台「连接信息」下载 kubeconfig，放到 ~/.kube/config
kubectl get nodes         # 验证连接
```

---

## 2. 打镜像

项目结构里两个东西要打镜像：

- **api**：FastAPI 后端，Dockerfile 在 `apps/api/Dockerfile`（已有）
- **web**：Vite 静态产物 + Nginx，**新建一个 Dockerfile**

### 2.1 API 镜像（已有，无需改）

`apps/api/Dockerfile` 现在的产物已经能直接上 K8s。本地构建测试：

```bash
cd C:/work/md_file/weixin/yimei-rfp/venus-4s
docker build -f apps/api/Dockerfile -t venus-api:dev .
docker run --rm -p 8000:8000 --env-file /tmp/api.env venus-api:dev
curl http://localhost:8000/health
```

### 2.2 Web 镜像（新增）

ECS 版是把 `dist/` scp 上去给 Nginx 挂载。K8s 里要把 web 也打成镜像。

在 `apps/web/Dockerfile` 新建：

```dockerfile
# ===== build stage =====
FROM node:20-alpine AS builder
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app
# monorepo 上下文：workspace + shared-types 都要拷
COPY pnpm-workspace.yaml package.json* ./
COPY packages/shared-types ./packages/shared-types
COPY apps/web ./apps/web

WORKDIR /app/apps/web
RUN pnpm install --frozen-lockfile
RUN pnpm build

# ===== runtime stage =====
FROM nginx:1.27-alpine
COPY infra/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -qO- http://localhost/healthz || exit 1
```

配套 `infra/nginx/web.conf`（容器内的 nginx 只服务静态，不做 TLS，TLS 由 Ingress 终止）：

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;

    location /healthz { return 200 "ok\n"; }

    location / {
        try_files $uri $uri/ /index.html;   # SPA fallback
        add_header Cache-Control "no-cache";
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

构建测试：

```bash
docker build -f apps/web/Dockerfile -t venus-web:dev .
docker run --rm -p 8080:80 venus-web:dev
# 浏览器访问 http://localhost:8080
```

### 2.3 打 tag 规范

```bash
# 用 git short-sha 当 tag（不可变），latest 只在 dev 集群用
SHA=$(git rev-parse --short HEAD)   # 或手工：20260630-001
REGISTRY=registry.cn-hangzhou.aliyuncs.com
NS=venus

docker build -f apps/api/Dockerfile -t $REGISTRY/$NS/api:$SHA -t $REGISTRY/$NS/api:latest .
docker build -f apps/web/Dockerfile -t $REGISTRY/$NS/web:$SHA -t $REGISTRY/$NS/web:latest .
```

---

## 3. 推送到 ACR

### 3.1 创建命名空间和仓库

ACR 控制台 → 实例 → 命名空间 `venus`（私有）→ 仓库 `api` / `web`（私有）。

### 3.2 登录 + push

```bash
# 用 ACR 控制台「访问凭证」里的临时密码（推荐）或固定密码
docker login --username=<acr-user>@<aliyun-uid> registry.cn-hangzhou.aliyuncs.com
# 输入密码

docker push $REGISTRY/$NS/api:$SHA
docker push $REGISTRY/$NS/api:latest
docker push $REGISTRY/$NS/web:$SHA
docker push $REGISTRY/$NS/web:latest
```

### 3.3 让 K8s 能拉私有镜像

```bash
kubectl create namespace venus-prod

kubectl -n venus-prod create secret docker-registry acr-cred \
    --docker-server=registry.cn-hangzhou.aliyuncs.com \
    --docker-username='<acr-user>@<aliyun-uid>' \
    --docker-password='<acr-password>' \
    --docker-email='ops@example.com'
```

**生产推荐**：ACK 控制台 → 配置项 → 免密插件，直接打通 ACR，省掉这个 Secret。

---

## 4. K8s 资源清单

所有 YAML 放 `infra/k8s/`。下面给完整一套，照搬就能跑。

### 4.1 目录结构

```
infra/k8s/
├── 00-namespace.yaml
├── 01-configmap.yaml
├── 02-secret.example.yaml      # 模板，真实值不提交
├── 10-api-deployment.yaml
├── 11-api-service.yaml
├── 12-api-hpa.yaml
├── 20-web-deployment.yaml
├── 21-web-service.yaml
├── 30-cron-deployment.yaml
├── 40-migrate-job.yaml         # 一次性数据库迁移
├── 50-ingress.yaml
└── kustomization.yaml          # 把上面打包
```

### 4.2 Namespace

`00-namespace.yaml`：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: venus-prod
```

### 4.3 ConfigMap（非敏感配置）

`01-configmap.yaml`：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: venus-prod
data:
  APP_ENV: "prod"
  APP_DEBUG: "false"
  LLM_PROVIDER: "qwen"
  LLM_QWEN_BASE_URL: "http://llm-service.llm-prod.svc.cluster.local:8080"
  OSS_ENDPOINT: "https://oss-cn-hangzhou.aliyuncs.com"
  OSS_INTERNAL_ENDPOINT: "https://oss-cn-hangzhou-internal.aliyuncs.com"
  OSS_BUCKET: "venus-prod"
  ALI_SMS_SIGN: "薇分美学"
  ALI_SMS_TEMPLATE_LOGIN: "SMS_XXXXXXX"
```

### 4.4 Secret（敏感配置）

`02-secret.example.yaml`（**仅模板，真值用 kubectl 直接创建或用 KMS**）：

```bash
# 生成 .env.prod 后一条命令导入
kubectl -n venus-prod create secret generic api-secret \
    --from-env-file=/tmp/.env.prod
```

`.env.prod` 的内容（参考现有 `config/prod.secrets.example`）：

```env
DATABASE_URL=mysql+aiomysql://venus:<PASS>@rm-xxxxx.mysql.rds.aliyuncs.com:3306/venus
REDIS_URL=redis://:<PASS>@r-xxxxx.redis.rds.aliyuncs.com:6379/0
JWT_SECRET=<openssl rand -hex 32>
PHONE_DEK_BASE64=<openssl rand -base64 32>
PHONE_HMAC_KEY=<openssl rand -hex 16>
ALI_ACCESS_KEY_ID=LTAI5t...
ALI_ACCESS_KEY_SECRET=...
OSS_STS_ROLE_ARN=acs:ram::xxxxx:role/venus-oss-sts
```

**更推荐**：用 **阿里云 KMS + ack-secret-manager**，把秘钥放 KMS 凭据管家，K8s 里只挂引用，秘钥不落 etcd。

### 4.5 API Deployment

`10-api-deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: venus-prod
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      imagePullSecrets:
        - name: acr-cred              # 如果用了 ACR 免密插件可删
      containers:
        - name: api
          image: registry.cn-hangzhou.aliyuncs.com/venus/api:REPLACE_ME_SHA
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef: { name: api-config }
            - secretRef:    { name: api-secret }
          resources:
            requests: { cpu: "200m", memory: "512Mi" }
            limits:   { cpu: "1000m", memory: "1Gi"  }
          readinessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 30
            periodSeconds: 15
```

### 4.6 API Service

`11-api-service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: venus-prod
spec:
  selector: { app: api }
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

### 4.7 API HPA（弹性伸缩）

`12-api-hpa.yaml`：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
  namespace: venus-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
```

### 4.8 Web Deployment / Service

`20-web-deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: web, namespace: venus-prod }
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      imagePullSecrets: [{ name: acr-cred }]
      containers:
        - name: web
          image: registry.cn-hangzhou.aliyuncs.com/venus/web:REPLACE_ME_SHA
          ports: [{ containerPort: 80 }]
          resources:
            requests: { cpu: "50m", memory: "64Mi" }
            limits:   { cpu: "200m", memory: "128Mi" }
          readinessProbe:
            httpGet: { path: /healthz, port: 80 }
```

`21-web-service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata: { name: web, namespace: venus-prod }
spec:
  selector: { app: web }
  ports: [{ port: 80, targetPort: 80 }]
  type: ClusterIP
```

### 4.9 Cron Deployment

`30-cron-deployment.yaml`（worker 进程，不暴露端口）：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: cron, namespace: venus-prod }
spec:
  replicas: 1                  # 必须 1，避免任务重复
  strategy: { type: Recreate } # 先停后起，避免两个进程并发
  selector: { matchLabels: { app: cron } }
  template:
    metadata: { labels: { app: cron } }
    spec:
      imagePullSecrets: [{ name: acr-cred }]
      containers:
        - name: cron
          image: registry.cn-hangzhou.aliyuncs.com/venus/api:REPLACE_ME_SHA
          command: ["python", "-m", "app.cron"]
          envFrom:
            - configMapRef: { name: api-config }
            - secretRef:    { name: api-secret }
          resources:
            requests: { cpu: "100m", memory: "256Mi" }
            limits:   { cpu: "500m", memory: "512Mi" }
```

### 4.10 数据库迁移 Job

`40-migrate-job.yaml`（每次升级前跑一次）：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: migrate-REPLACE_ME_SHA   # 每次部署改名，免得复用旧 Job
  namespace: venus-prod
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      imagePullSecrets: [{ name: acr-cred }]
      containers:
        - name: migrate
          image: registry.cn-hangzhou.aliyuncs.com/venus/api:REPLACE_ME_SHA
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - secretRef: { name: api-secret }
```

### 4.11 Ingress（域名 + TLS）

`50-ingress.yaml`：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: venus
  namespace: venus-prod
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/proxy-body-size: "20m"      # 上传图片
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"   # LLM 长响应
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
    - hosts: [venus.example.com]
      secretName: venus-tls
  rules:
    - host: venus.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service: { name: api, port: { number: 8000 } }
          - path: /health
            pathType: Exact
            backend:
              service: { name: api, port: { number: 8000 } }
          - path: /
            pathType: Prefix
            backend:
              service: { name: web, port: { number: 80 } }
```

### 4.12 Kustomization（统一替换镜像 tag）

`infra/k8s/kustomization.yaml`：

```yaml
namespace: venus-prod
resources:
  - 00-namespace.yaml
  - 01-configmap.yaml
  - 10-api-deployment.yaml
  - 11-api-service.yaml
  - 12-api-hpa.yaml
  - 20-web-deployment.yaml
  - 21-web-service.yaml
  - 30-cron-deployment.yaml
  - 50-ingress.yaml

images:
  - name: registry.cn-hangzhou.aliyuncs.com/venus/api
    newTag: REPLACE_ME_SHA
  - name: registry.cn-hangzhou.aliyuncs.com/venus/web
    newTag: REPLACE_ME_SHA
```

部署时一条命令替 tag：

```bash
cd infra/k8s
kustomize edit set image \
    registry.cn-hangzhou.aliyuncs.com/venus/api=$REGISTRY/$NS/api:$SHA \
    registry.cn-hangzhou.aliyuncs.com/venus/web=$REGISTRY/$NS/web:$SHA
kubectl apply -k .
```

---

## 5. 部署执行（首次）

```bash
# 1. 装 Ingress Controller（集群级，一次性）
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx --create-namespace \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/alibaba-cloud-loadbalancer-spec"=slb.s2.small

# 等它给一个公网 EIP
kubectl -n ingress-nginx get svc ingress-nginx-controller -w
# EXTERNAL-IP 出来后记下来，DNS 配它

# 2. 建 namespace + secret + configmap
kubectl apply -f infra/k8s/00-namespace.yaml
kubectl -n venus-prod create secret generic api-secret --from-env-file=/tmp/.env.prod
kubectl apply -f infra/k8s/01-configmap.yaml

# 3. 准备 TLS 证书（甲方提供的 fullchain + privkey）
kubectl -n venus-prod create secret tls venus-tls \
    --cert=/path/to/fullchain.pem \
    --key=/path/to/privkey.pem

# 4. 跑迁移 Job
kubectl apply -f infra/k8s/40-migrate-job.yaml
kubectl -n venus-prod logs -f job/migrate-$SHA

# 5. 部署应用
kubectl apply -k infra/k8s/

# 6. 看状态
kubectl -n venus-prod get pods,svc,ingress,hpa
kubectl -n venus-prod rollout status deploy/api
kubectl -n venus-prod rollout status deploy/web
```

---

## 6. 域名 → 服务的完整链路

### 6.1 DNS 配置

阿里云控制台 → 云解析 DNS → `example.com` → 添加记录：

| 记录类型 | 主机记录 | 记录值                                   |
| -------- | -------- | ---------------------------------------- |
| A        | venus    | `<ingress-nginx LoadBalancer EXTERNAL-IP>` |

如果用阿里云 SLB（CLB）跨域用 CNAME 也行：

| 记录类型 | 主机记录 | 记录值                       |
| -------- | -------- | ---------------------------- |
| CNAME    | venus    | `xxxxx.slb.aliyuncs.com`     |

### 6.2 流量走向（关键链路）

```
venus.example.com
   │ ① DNS 解析 → SLB EXTERNAL-IP (公网)
   ▼
SLB (TCP 443)
   │ ② 转发到 ACK 节点的 NodePort
   ▼
ingress-nginx Pod (Service type=LoadBalancer)
   │ ③ TLS 终止 (用 secret/venus-tls)
   │ ④ 看 Host + Path 匹配 Ingress 规则
   ▼
   ├─ Path=/api/*  → Service/api  → Deployment/api Pods (FastAPI :8000)
   ├─ Path=/health → Service/api  → Deployment/api Pods
   └─ Path=/*      → Service/web  → Deployment/web Pods (Nginx :80)
```

### 6.3 证书自动续期（可选，比手动放 PEM 强）

装 cert-manager + 阿里云 DNS01 插件，证书 90 天自动续：

```bash
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager --create-namespace \
    --set installCRDs=true
```

然后建一个 `ClusterIssuer` 用 Let's Encrypt + 阿里云 DNS 验证，Ingress 加注解 `cert-manager.io/cluster-issuer: letsencrypt-prod`，`venus-tls` 这个 Secret 会自动生成和续期。具体配置见 cert-manager 阿里云 webhook 文档。

### 6.4 微信公众号回调

**别忘了** ICP 备案完域名后，去公众号后台：

- 设置与开发 → 公众号设置 → 功能设置 → **业务域名** 加 `venus.example.com`
- 把校验文件 `MP_verify_xxx.txt` 放到 web 镜像的 `public/` 下重新构建，否则微信侧 H5 跳转 / JSSDK 都会被拦

---

## 7. 验证

```bash
# 1. Ingress 拿到外网 IP
kubectl -n ingress-nginx get svc ingress-nginx-controller

# 2. 在 IP 解析生效前用 --resolve 临时测
curl -k --resolve venus.example.com:443:<EXTERNAL-IP> \
    https://venus.example.com/health

# 3. DNS 生效后正常验证
curl -sf https://venus.example.com/health
HOST=https://venus.example.com bash scripts/smoke.sh

# 4. 看真实流量
kubectl -n venus-prod logs -f deploy/api --tail=100
kubectl -n venus-prod top pod
```

---

## 8. 升级 / 回滚

### 升级（CI/CD 之外的手动姿势）

```bash
NEW_SHA=20260701-abc1234
cd infra/k8s
kustomize edit set image \
    registry.cn-hangzhou.aliyuncs.com/venus/api=$REGISTRY/$NS/api:$NEW_SHA \
    registry.cn-hangzhou.aliyuncs.com/venus/web=$REGISTRY/$NS/web:$NEW_SHA

# 先跑迁移
sed "s/REPLACE_ME_SHA/$NEW_SHA/g" 40-migrate-job.yaml | kubectl apply -f -
kubectl -n venus-prod wait --for=condition=complete --timeout=300s job/migrate-$NEW_SHA

# 再升级业务
kubectl apply -k .
kubectl -n venus-prod rollout status deploy/api
```

### 回滚（30 秒搞定）

```bash
kubectl -n venus-prod rollout undo deploy/api
kubectl -n venus-prod rollout undo deploy/web
```

或者回到具体版本：

```bash
kubectl -n venus-prod rollout history deploy/api
kubectl -n venus-prod rollout undo deploy/api --to-revision=3
```

**注意**：Alembic 迁移**不会自动回滚**，如果是破坏性迁移（删列、改类型），代码回滚后 schema 还在新版，要么手动 `alembic downgrade`，要么前向兼容设计（推荐：删列分两步发布）。

---

## 9. CI/CD（GitHub Actions 示例）

`.github/workflows/deploy.yml`：

```yaml
name: deploy
on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    env:
      REGISTRY: registry.cn-hangzhou.aliyuncs.com
      NS: venus
    steps:
      - uses: actions/checkout@v4

      - name: Login ACR
        run: echo "${{ secrets.ACR_PASS }}" | docker login $REGISTRY -u "${{ secrets.ACR_USER }}" --password-stdin

      - name: Build & push
        run: |
          SHA=${GITHUB_SHA::7}
          docker build -f apps/api/Dockerfile -t $REGISTRY/$NS/api:$SHA .
          docker build -f apps/web/Dockerfile -t $REGISTRY/$NS/web:$SHA .
          docker push $REGISTRY/$NS/api:$SHA
          docker push $REGISTRY/$NS/web:$SHA
          echo "SHA=$SHA" >> $GITHUB_ENV

      - name: Setup kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > ~/.kube/config

      - name: Run migration
        run: |
          sed "s/REPLACE_ME_SHA/$SHA/g" infra/k8s/40-migrate-job.yaml | kubectl apply -f -
          kubectl -n venus-prod wait --for=condition=complete --timeout=300s job/migrate-$SHA

      - name: Deploy
        run: |
          cd infra/k8s
          kustomize edit set image \
            $REGISTRY/$NS/api=$REGISTRY/$NS/api:$SHA \
            $REGISTRY/$NS/web=$REGISTRY/$NS/web:$SHA
          kubectl apply -k .
          kubectl -n venus-prod rollout status deploy/api --timeout=300s
          kubectl -n venus-prod rollout status deploy/web --timeout=300s

      - name: Smoke test
        run: HOST=https://${{ secrets.PUBLIC_HOST }} bash scripts/smoke.sh
```

需要的 GitHub Secrets：`ACR_USER` / `ACR_PASS` / `KUBECONFIG_B64`（`cat ~/.kube/config | base64 -w0`）/ `PUBLIC_HOST`。

---

## 10. 监控 / 日志 / 告警

| 维度       | 方案                                                                 |
| ---------- | -------------------------------------------------------------------- |
| 指标       | ACK 内置 Prometheus + Grafana，看 CPU/内存/QPS/P99                   |
| 日志       | 装 ACK 日志服务组件，自动采到阿里云 SLS Project `venus-prod`         |
| APM        | 阿里云 ARMS Agent 注入到 API Pod（Java/Python 都支持）              |
| 告警       | SLS 告警 → 飞书 webhook，规则照搬 `DEPLOY.md` §8                    |
| 健康       | Ingress 5xx 比例 / Pod CrashLoopBackOff / HPA 触顶 都建告警         |

---

## 11. 成本估算（生产小规模参考）

| 资源                        | 规格                  | 月成本 (¥) |
| --------------------------- | --------------------- | ---------- |
| ACK Pro 托管版              | 集群管理费            | ~330       |
| ECS worker × 3              | 4C8G                  | ~900       |
| SLB                         | slb.s2.small + 5M     | ~250       |
| RDS MySQL                   | 2C4G + 100G ESSD      | ~600       |
| 云数据库 Tair               | 1G 主从               | ~250       |
| OSS                         | 100G + 流量           | ~50        |
| ACR                         | 个人版                | 免费       |
| **合计**                    |                       | **~2400**  |

ECS+Compose 方案大概 ~600，K8s 多出来的钱买的是：弹性伸缩、滚动发布零停机、多副本高可用、运维标准化。**如果月活 < 1 万，老老实实用 ECS 方案就行**。

---

## 12. 与 ECS 版的取舍

| 场景                     | 选哪个              |
| ------------------------ | ------------------- |
| MVP 验证 / 单机够用      | **ECS + Compose**   |
| 月 PV < 10w              | **ECS + Compose**   |
| 需要弹性伸缩 / 多机房灾备 | K8s                 |
| 团队已有 K8s 运维能力     | K8s                 |
| 需要金丝雀 / A/B 发布     | K8s                 |
| 只有一个后端开发          | **ECS + Compose**   |
