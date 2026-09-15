# 单机 k3s 部署手册（同 ECS 跑业务 + 模型服务）

> **懒人通道**：想直接跑一键脚本请看 [infra/k3s/README.md](../../infra/k3s/README.md)，脚本已经把本文档 §2~§9 的所有操作自动化了。本文档保留给需要理解原理、排查问题、或者定制化的读者。

> 这是**单机 k3s** 版部署文档，适用场景：
>
> - 一台阿里云 ECS 上同时跑「业务 Pod」和「模型服务 Pod」，两者通过 k8s Service 互访；
> - 想要 k8s 的特性（Service DNS、健康检查、滚动升级、NetworkPolicy），但不想为 ACK Pro 管理费（约 ¥460/月）+ SLB（约 ¥250/月）额外买单；
> - 已经完成 [02-部署实施.md](../02-部署实施.md) §1~§3 的镜像构建与推送。
>
> 若要用阿里云托管 K8s（ACK），请阅 [DEPLOY_K8S.md](./DEPLOY_K8S.md)；若只是 Docker Compose 起两个容器，请阅 [02-部署实施.md](../02-部署实施.md)。

---

## 0. 架构概览

```
                           用户
                            │ HTTPS
                            ▼
                    ┌──────────────┐
                    │ 阿里云 SLB    │  （可选，不用也行，nginx 直接监听 443）
                    └──────┬───────┘
                           │
        ┌──────────────────┼─────────────────────────────┐
        │           单台 ECS（k3s server 模式）            │
        │                  │                              │
        │      ┌───────────▼───────────┐                  │
        │      │  Traefik / nginx      │  80/443          │
        │      │  Ingress Controller   │                  │
        │      └───────────┬───────────┘                  │
        │                  │                              │
        │  ┌───────────────┼──────────────────────────┐   │
        │  │  ns: venus-prod                          │   │
        │  │  ┌────────────▼──────┐                   │   │
        │  │  │ Service: api      │  ClusterIP :8000  │   │
        │  │  └────────────┬──────┘                   │   │
        │  │               ▼                          │   │
        │  │  ┌───────────────────┐                   │   │
        │  │  │ Deployment: api   │  1~2 副本         │   │
        │  │  └────────────┬──────┘                   │   │
        │  └───────────────┼──────────────────────────┘   │
        │                  │ 通过 Service DNS 访问          │
        │                  │ http://llm-service            │
        │                  │   .llm-prod.svc.cluster.local │
        │                  │   :8080                       │
        │                  ▼                              │
        │  ┌───────────────────────────────────────────┐  │
        │  │  ns: llm-prod                             │  │
        │  │  ┌───────────────────┐  ┌──────────────┐  │  │
        │  │  │ Service:          │  │ Deployment:  │  │  │
        │  │  │ llm-service       │◀─│ llm-service  │  │  │
        │  │  │ ClusterIP :8080   │  │              │  │  │
        │  │  └───────────────────┘  └──────────────┘  │  │
        │  └───────────────────────────────────────────┘  │
        │                                                 │
        │  数据层走托管服务（不进 k3s）:                    │
        │  RDS MySQL / Tair Redis / OSS / SMS / 内容审核    │
        └─────────────────────────────────────────────────┘
```

**关键点**：

- 业务 Pod 通过 `http://llm-service.llm-prod.svc.cluster.local:8080` 访问模型 Pod，**不要用 127.0.0.1**（Pod 之间是独立的网络命名空间，即便在同一台机上）。
- 数据库、Redis 仍然用云托管，不进 k3s。理由与 ACK 方案相同（备份/HA 自己扛不动）。
- 模型服务和业务分两个 namespace，便于用 NetworkPolicy 做隔离，也方便未来把模型服务独立到其他机器。

---

## 1. 前置条件

### 1.1 ECS 规格建议

| 用途 | 最低配置 | 推荐配置 |
|---|---|---|
| 仅业务 Pod（api + web） | 2C4G | 4C8G |
| 业务 + 模型（CPU 推理，小模型） | 8C16G | 16C32G |
| 业务 + 模型（GPU，7B 量级） | ecs.gn6i-c4g1.xlarge（T4 16G 显存） | ecs.gn7i-c8g1.2xlarge（A10 24G 显存） |
| 业务 + 模型代理（模型调阿里云百炼 API，不本地推理） | 2C4G | 4C8G |

其他：

- 系统盘 ≥ **100 GB**（模型镜像常有几十 GB，加上 containerd 镜像层缓存）；
- OS：CentOS 7.9 / Alibaba Cloud Linux 3 / Ubuntu 22.04；
- 与 RDS/Redis/OSS **同 VPC 同可用区**（内网互通、免公网流量费）。

### 1.2 已经完成的准备工作

参照 [02-部署实施.md](../02-部署实施.md)：

- [ ] §2 构建配置（`infra/build.conf`、`config/prod.baseline.env`）已填写；
- [ ] §3 api / web 镜像已推送到 ACR，能通过 `docker manifest inspect` 看到；
- [ ] §6 `/etc/venus-4s/.env` 里的密钥已准备好（复用同一份，仅路径不同，见 §5）。

---

## 2. 在 ECS 上安装 k3s

SSH 登录 ECS：

```bash
ssh root@<ECS 公网 IP>
```

### 2.1 一键装 k3s

k3s 官方脚本一条命令搞定，中国大陆用户走镜像加速版：

```bash
# 走阿里云 OSS 镜像（速度快、不需要翻墙）
curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | \
    INSTALL_K3S_MIRROR=cn \
    INSTALL_K3S_EXEC="--disable=traefik --write-kubeconfig-mode=644" \
    sh -
```

参数说明：

| 参数 | 作用 |
|---|---|
| `INSTALL_K3S_MIRROR=cn` | 从国内镜像下载 k3s 二进制 |
| `--disable=traefik` | 关掉 k3s 自带的 Traefik（如果你已有 nginx 或想用 ingress-nginx，加这个）。**如果你就想直接用 Traefik，把这个删掉** |
| `--write-kubeconfig-mode=644` | 让非 root 用户也能读 kubeconfig |

安装完成会输出：

```
[INFO]  systemd: Starting k3s
```

### 2.2 验证安装

```bash
kubectl get nodes
```

预期输出（等 30 秒左右）：

```
NAME           STATUS   ROLES                  AGE   VERSION
iZbp1abc123Z   Ready    control-plane,master   30s   v1.30.x+k3s1
```

再看系统 Pod：

```bash
kubectl -n kube-system get pods
```

`coredns` / `local-path-provisioner` / `metrics-server` 应该都是 `Running`。

### 2.3 kubeconfig 位置

k3s 把 kubeconfig 写在 `/etc/rancher/k3s/k3s.yaml`，`kubectl` 默认会读它。如果你想在**本地机器**上远程管理这台 k3s，把这个文件复制回本地：

```bash
# 在 ECS 上
cat /etc/rancher/k3s/k3s.yaml

# 复制到本地 ~/.kube/config-k3s，并把里面的 127.0.0.1 改成 ECS 公网 IP
# 用 KUBECONFIG 环境变量切换：export KUBECONFIG=~/.kube/config-k3s
```

> **安全提醒**：kubeconfig 里的 client-certificate 权限极高，等同 root。别提交到 git，别放 IM。

---

## 3. 让 k3s 能拉 ACR 私有镜像

k3s 用的是 containerd（不是 docker），配置方式和 ACK 稍有不同。有**两种做法**，二选一：

### 3.1 方式 A（推荐）：配置 containerd registry mirror

一次性配置，之后所有 namespace 拉 ACR 镜像都免密。

```bash
sudo mkdir -p /etc/rancher/k3s
sudo tee /etc/rancher/k3s/registries.yaml > /dev/null <<'EOF'
mirrors:
  registry.cn-hangzhou.aliyuncs.com:
    endpoint:
      - "https://registry-vpc.cn-hangzhou.aliyuncs.com"  # 走 VPC 内网，免流量费
configs:
  registry-vpc.cn-hangzhou.aliyuncs.com:
    auth:
      username: "<ACR 用户名>@<阿里云 UID>"
      password: "<ACR 固定密码>"
EOF

sudo systemctl restart k3s
```

**要点**：

- `endpoint` 里填 **VPC 内网地址**（`registry-vpc.*`），k3s 拉镜像走内网带宽，不占公网流量费；
- `username` / `password` 从 ACR 控制台「访问凭证」页获取「固定密码」；
- 配置错了会导致新 Pod `ImagePullBackOff`，改完必须 `systemctl restart k3s` 生效。

### 3.2 方式 B：每个 namespace 单独建 imagePullSecret

如果你不方便动 `/etc/rancher/k3s/registries.yaml`（比如 ECS 权限不够），退回到经典方式：

```bash
kubectl create namespace venus-prod
kubectl create namespace llm-prod

for ns in venus-prod llm-prod; do
  kubectl -n $ns create secret docker-registry acr-cred \
    --docker-server=registry.cn-hangzhou.aliyuncs.com \
    --docker-username='<ACR 用户名>@<阿里云 UID>' \
    --docker-password='<ACR 固定密码>' \
    --docker-email='ops@example.com'
done
```

之后每个 Deployment 都要显式声明 `imagePullSecrets: [{ name: acr-cred }]`（现有 `infra/k8s/10-api-deployment.yaml` 已经写了）。

> **本文后续所有 yaml 都保留了 `imagePullSecrets` 字段**，即使你用了方式 A 也无害（会被忽略）。

---

## 4. 建命名空间

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: venus-prod
---
apiVersion: v1
kind: Namespace
metadata:
  name: llm-prod
EOF
```

验证：

```bash
kubectl get ns | grep -E 'venus-prod|llm-prod'
```

---

## 5. 部署业务 Pod（复用 `infra/k8s/`）

现有 `infra/k8s/` 下的 yaml 是按 ACK 场景写的，在 k3s 上**几乎不用改**，只有两处需要注意：

### 5.1 把 kustomization 里的 ingress 换成单机版

k3s 单机场景下，`50-ingress.yaml` 里的 nginx-ingress-controller 用不了（你没装 helm chart）。如果你**继续用现有 web 容器里的 nginx** 做 TLS 终止和路由（跟 §02 一致），可以在 kustomization 里注释掉 ingress：

编辑 `infra/k8s/kustomization.yaml`：

```yaml
resources:
  - 00-namespace.yaml
  - 01-configmap.yaml
  - 10-api-deployment.yaml
  - 11-api-service.yaml
  - 12-api-hpa.yaml
  - 20-web-deployment.yaml
  - 21-web-service.yaml
  - 30-cron-deployment.yaml
  # - 50-ingress.yaml           # 单机 k3s 场景先不启用
```

然后把 web Service 类型改成 `NodePort`，暴露到宿主机端口：

编辑 `infra/k8s/21-web-service.yaml`：

```yaml
spec:
  selector:
    app: web
  type: NodePort              # 从 ClusterIP 改成 NodePort
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080         # 宿主机的 30080 端口 → web
    - port: 443
      targetPort: 443
      nodePort: 30443
```

配合 ECS 安全组开放 30080/30443，或者在前面挂一个 SLB 转发 443 → 30443。

> **想用真正的 Ingress？** 装 [ingress-nginx](https://kubernetes.github.io/ingress-nginx/deploy/#quick-start)（`helm install ...`），或者装 k3s 自带的 Traefik（安装时别加 `--disable=traefik`）。

### 5.2 建 ConfigMap / Secret

ConfigMap 直接 apply（现有 `01-configmap.yaml` 已经把 `LLM_QWEN_BASE_URL` 指向 `http://llm-service.llm-prod.svc.cluster.local:8080`）：

```bash
kubectl apply -f infra/k8s/01-configmap.yaml
```

Secret 从 `/etc/venus-4s/.env`（跟 [02-部署实施.md §6](../02-部署实施.md#6-在-ecs-上配置密钥文件) 一致）导入：

```bash
kubectl -n venus-prod create secret generic api-secret \
    --from-env-file=/etc/venus-4s/.env
```

> **注意**：`/etc/venus-4s/.env` 里如果有 `APP_ENV=` 这类非敏感项，也会被塞进 Secret；不影响功能，但更规范的做法是把敏感项单独拆一份 `.env.secret` 只导入密钥。

### 5.3 部署

```bash
cd infra/k8s
kubectl apply -k .
```

看 Pod 起没起来：

```bash
kubectl -n venus-prod get pods -w
```

预期：

```
NAME                   READY   STATUS    RESTARTS   AGE
api-7c9d8b7f9d-abcde   1/1     Running   0          30s
api-7c9d8b7f9d-fghij   1/1     Running   0          30s
web-6b5f4c3d2e-klmno   1/1     Running   0          30s
```

不 Ready 的话看日志：

```bash
kubectl -n venus-prod logs deploy/api --tail=100
kubectl -n venus-prod describe pod <pod-name>
```

常见错误参考 [02-部署实施.md §11](../02-部署实施.md#11-故障排查)。

---

## 6. 部署模型服务 Pod

在 `infra/k8s/` 下新建 `llm/` 子目录（**不要**跟业务 Deployment 混一起，方便独立维护）：

```
infra/k8s/llm/
├── 00-namespace.yaml           # 已在 §4 建好，可省
├── 10-llm-deployment.yaml
├── 11-llm-service.yaml
└── 20-llm-networkpolicy.yaml   # §7 会用
```

### 6.1 Deployment 示例（按你的模型服务实际情况改）

假设你的模型服务镜像已经推到 ACR：`registry.cn-hangzhou.aliyuncs.com/venus/llm:v1.0.0`，监听 8080。

`infra/k8s/llm/10-llm-deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-service
  namespace: llm-prod
  labels:
    app: llm-service
spec:
  replicas: 1                     # 单机 k3s 下模型服务通常只跑一个副本
  strategy:
    type: Recreate                # 显存有限，不能滚动（新旧共存会 OOM）
  selector:
    matchLabels:
      app: llm-service
  template:
    metadata:
      labels:
        app: llm-service
    spec:
      imagePullSecrets:
        - name: acr-cred          # 方式 A 已配 registries.yaml 的话可省
      containers:
        - name: llm
          image: registry.cn-hangzhou.aliyuncs.com/venus/llm:v1.0.0
          ports:
            - name: http
              containerPort: 8080
          env:
            # 模型服务自己的 API Key，来自另一份 Secret（§6.2）
            - name: SERVICE_API_KEY
              valueFrom:
                secretKeyRef:
                  name: llm-secret
                  key: SERVICE_API_KEY
          resources:
            requests:
              cpu: "1000m"
              memory: "4Gi"
            limits:
              cpu: "4000m"
              memory: "8Gi"
              # GPU 场景加：nvidia.com/gpu: "1"
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30   # 模型加载慢，给足时间
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 6
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 120
            periodSeconds: 30
```

**几个要点**：

- `strategy: Recreate`：模型 Pod 通常吃显存/内存，滚动升级时新旧 Pod 共存会 OOM。宁可停几秒也别 OOM。
- `initialDelaySeconds` 给大：模型加载常常要几十秒到几分钟。
- GPU 场景：需要先在 ECS 上装 nvidia-container-toolkit，再给 k3s 加 `--default-runtime=nvidia`（本文档不展开，参考 [k3s GPU 文档](https://docs.k3s.io/advanced#nvidia-container-runtime-support)）。

### 6.2 模型服务的 Secret（API Key 等）

```bash
# 生成一个强随机 key，业务侧调用时带在 Authorization header 里
LLM_KEY=$(openssl rand -hex 32)

kubectl -n llm-prod create secret generic llm-secret \
    --from-literal=SERVICE_API_KEY="$LLM_KEY"

# 同时把这个 key 加到业务侧的 Secret 里，供 api Pod 调用时使用
kubectl -n venus-prod patch secret api-secret \
    --patch="{\"stringData\":{\"LLM_SERVICE_API_KEY\":\"$LLM_KEY\"}}"
```

业务代码里读 `LLM_SERVICE_API_KEY`，请求头加 `Authorization: Bearer ${LLM_SERVICE_API_KEY}`。

### 6.3 部署

```bash
kubectl apply -f infra/k8s/llm/10-llm-deployment.yaml
kubectl -n llm-prod get pods -w
```

---

## 7. 建 ClusterIP Service（业务 ↔ 模型）

### 7.1 模型服务 Service

`infra/k8s/llm/11-llm-service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: llm-service            # 关键：这个名字决定了 DNS
  namespace: llm-prod
  labels:
    app: llm-service
spec:
  selector:
    app: llm-service           # 匹配 Deployment 的 pod labels
  ports:
    - name: http
      port: 8080               # Service 对外端口（业务侧访问用这个）
      targetPort: 8080         # 转发到 Pod 里的端口
  type: ClusterIP              # 只在集群内可访问，最安全
```

应用：

```bash
kubectl apply -f infra/k8s/llm/11-llm-service.yaml
```

### 7.2 业务侧访问地址

Service 完整 DNS 是：

```
<service-name>.<namespace>.svc.cluster.local
```

对应到本例，业务 Pod 调用模型的 URL 是：

```
http://llm-service.llm-prod.svc.cluster.local:8080
```

`infra/k8s/01-configmap.yaml` 里的 `LLM_QWEN_BASE_URL` **已经**是这个值，无需修改。

**同 namespace 简写**：如果业务和模型放在**同一个 namespace**，可以省略 `.namespace.svc.cluster.local`，直接写 `http://llm-service:8080`。本方案分了两个 ns，必须写全 FQDN。

### 7.3 验证服务连通性

在业务 Pod 里 curl 一下模型服务：

```bash
kubectl -n venus-prod exec -it deploy/api -- \
    curl -sf http://llm-service.llm-prod.svc.cluster.local:8080/health
```

预期返回模型服务的健康检查响应。如果超时：

- `kubectl -n llm-prod get svc llm-service` 看 CLUSTER-IP 有没有；
- `kubectl -n llm-prod get endpoints llm-service` 看 Endpoints 有没有 Pod IP（如果为空说明 selector 没匹配上）；
- `kubectl -n venus-prod exec deploy/api -- nslookup llm-service.llm-prod.svc.cluster.local` 看 DNS 能否解析。

---

## 8. 用 NetworkPolicy 限制访问（可选但推荐）

只让 `venus-prod/api` 能访问 `llm-prod/llm-service`，其他 Pod 一律拒绝。k3s 从 v1.21+ 内置了 kube-router NetworkPolicy 实现，直接 apply 就生效。

`infra/k8s/llm/20-llm-networkpolicy.yaml`：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-service-allow-api
  namespace: llm-prod
spec:
  podSelector:
    matchLabels:
      app: llm-service              # 保护对象：模型 Pod
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: venus-prod
          podSelector:
            matchLabels:
              app: api               # 只放行业务 api Pod
      ports:
        - protocol: TCP
          port: 8080
```

应用：

```bash
kubectl apply -f infra/k8s/llm/20-llm-networkpolicy.yaml
```

**验证**（会被拒的例子）：

```bash
# 临时起一个 busybox Pod，尝试访问模型服务
kubectl run test --rm -it --image=busybox --restart=Never -- \
    wget -T 3 -qO- http://llm-service.llm-prod.svc.cluster.local:8080/health
# 预期：超时 / 拒绝连接
```

从 api Pod 访问应该正常（§7.3 的命令）。

---

## 9. 完整部署清单（首次上线）

```bash
# 前置：镜像已推 ACR，/etc/venus-4s/.env 已填好

# 1. 装 k3s（§2）
curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | \
    INSTALL_K3S_MIRROR=cn \
    INSTALL_K3S_EXEC="--disable=traefik --write-kubeconfig-mode=644" \
    sh -

# 2. 配置 ACR 免密（§3.1）
sudo tee /etc/rancher/k3s/registries.yaml > /dev/null <<'EOF'
mirrors:
  registry.cn-hangzhou.aliyuncs.com:
    endpoint:
      - "https://registry-vpc.cn-hangzhou.aliyuncs.com"
configs:
  registry-vpc.cn-hangzhou.aliyuncs.com:
    auth:
      username: "<ACR用户名>@<UID>"
      password: "<ACR密码>"
EOF
sudo systemctl restart k3s

# 3. 上传 infra 目录到 ECS
# 本地：scp -r infra root@<ECS-IP>:/srv/venus-4s/
cd /srv/venus-4s/infra/k8s

# 4. 建 namespace
kubectl apply -f 00-namespace.yaml
kubectl create namespace llm-prod

# 5. 导 Secret（§5.2、§6.2）
kubectl -n venus-prod create secret generic api-secret \
    --from-env-file=/etc/venus-4s/.env

LLM_KEY=$(openssl rand -hex 32)
kubectl -n llm-prod create secret generic llm-secret \
    --from-literal=SERVICE_API_KEY="$LLM_KEY"
kubectl -n venus-prod patch secret api-secret \
    --patch="{\"stringData\":{\"LLM_SERVICE_API_KEY\":\"$LLM_KEY\"}}"

# 6. 跑数据库迁移（一次性）
kubectl -n venus-prod run migrate --rm -it --restart=Never \
    --image=registry.cn-hangzhou.aliyuncs.com/venus/api:v1.0.0 \
    --overrides='{"spec":{"containers":[{"name":"migrate","image":"registry.cn-hangzhou.aliyuncs.com/venus/api:v1.0.0","command":["alembic","upgrade","head"],"envFrom":[{"secretRef":{"name":"api-secret"}}]}]}}'

# 7. 部署业务
kubectl apply -k .

# 8. 部署模型服务
kubectl apply -f llm/

# 9. 验证
kubectl get pods -A
kubectl -n venus-prod exec deploy/api -- \
    curl -sf http://llm-service.llm-prod.svc.cluster.local:8080/health
```

---

## 10. 日常运维

### 10.1 升级镜像

```bash
NEW_TAG=v1.1.0
kubectl -n venus-prod set image deploy/api api=registry.cn-hangzhou.aliyuncs.com/venus/api:$NEW_TAG
kubectl -n venus-prod rollout status deploy/api

# 模型服务同理
kubectl -n llm-prod set image deploy/llm-service llm=registry.cn-hangzhou.aliyuncs.com/venus/llm:$NEW_TAG
```

### 10.2 回滚

```bash
kubectl -n venus-prod rollout undo deploy/api
kubectl -n venus-prod rollout history deploy/api    # 查历史
kubectl -n venus-prod rollout undo deploy/api --to-revision=3
```

### 10.3 看日志

```bash
kubectl -n venus-prod logs -f deploy/api --tail=200
kubectl -n llm-prod   logs -f deploy/llm-service --tail=200
```

### 10.4 进容器排查

```bash
kubectl -n venus-prod exec -it deploy/api -- /bin/sh
```

### 10.5 查看资源占用

```bash
kubectl top pod -A            # 需要 metrics-server（k3s 默认已装）
kubectl top node
```

### 10.6 备份 k3s 数据

k3s 的所有 k8s 元数据存在 `/var/lib/rancher/k3s/server/db/`（内置 SQLite）。定期备份：

```bash
# 停 k3s、拷贝、启回来（Pod 有短暂中断，选低峰期）
sudo systemctl stop k3s
sudo tar czf /root/k3s-backup-$(date +%F).tar.gz /var/lib/rancher/k3s/server/db /var/lib/rancher/k3s/server/token
sudo systemctl start k3s

# 或者用 etcd 存储 + 自动快照，参考 k3s 官方文档
```

**注意**：k3s 只备份 k8s 对象元数据。**业务数据在 RDS/OSS，跟 k3s 无关**，那部分按 [04-日常运维与排查.md](../04-日常运维与排查.md) 的备份策略执行。

---

## 11. 卸载 / 清理

```bash
# 卸载 k3s（会删掉所有 Pod、Service、镜像缓存）
/usr/local/bin/k3s-uninstall.sh
```

**卸载前请确认**：

- RDS、OSS、Redis 里的数据是否要保留（这些不在 k3s 里，卸载不受影响，但要确认后续访问方式）；
- ACR 里的镜像不受影响；
- ECS 本身不受影响（k3s 只装了几个二进制、几个 systemd 单元）。

---

## 12. 与 Docker Compose 方案的取舍

| 场景 | 选哪个 |
|---|---|
| 只跑 api + web + cron，无模型服务 | [02-部署实施.md](../02-部署实施.md)（Docker Compose） |
| 业务 + 模型服务同机，要 Service DNS / 健康检查 / 网络隔离 | **本文档（单机 k3s）** |
| 需要多机弹性伸缩、跨机房容灾、CI/CD 滚动发布 | [DEPLOY_K8S.md](./DEPLOY_K8S.md)（ACK） |
| 团队里没人懂 k8s，就想两个进程能跑 | Docker Compose |

**升级路径**：单机 k3s 未来可以平滑迁到 ACK。所有 yaml（Deployment / Service / NetworkPolicy）在两边通用，主要改的只是 Ingress 部分（k3s 内部端口 → ACK 用 SLB）。
