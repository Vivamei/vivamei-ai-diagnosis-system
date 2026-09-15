#!/usr/bin/env bash
# ==========================================================
# 单机 k3s 一键部署脚本
#
# 覆盖 docs/references/DEPLOY_K3S.md 第 2 ~ 9 章的所有操作：
#   1. 装 k3s
#   2. 配置 ACR 免密拉取（containerd registries.yaml）
#   3. 建 namespace (venus-prod / llm-prod)
#   4. 导入 Secret（业务 + LLM SERVICE_API_KEY）
#   5. 执行 Alembic 迁移（可选）
#   6. 部署业务 Deployment / Service / HPA / ConfigMap
#   7. 部署模型服务 Deployment / Service / NetworkPolicy
#   8. 打通业务 → 模型的健康检查
#
# 幂等：可以反复执行；已存在的资源自动跳过或更新。
#
# 用法：
#   cp infra/k3s/deploy.conf.example infra/k3s/deploy.conf
#   vim infra/k3s/deploy.conf     # 按注释填写
#   sudo bash infra/k3s/deploy.sh                    # 完整部署
#   sudo bash infra/k3s/deploy.sh --skip-install     # 跳过 k3s 安装（已装过）
#   sudo bash infra/k3s/deploy.sh --only-apps        # 只重新部署应用（跳过 k3s / ACR 配置）
#   sudo bash infra/k3s/deploy.sh --dry-run          # 只打印将执行的动作，不真正执行
# ==========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; BLU=$'\033[34m'; NC=$'\033[0m'
err()   { echo "${RED}✗ $*${NC}" >&2; }
ok()    { echo "${GRN}✓ $*${NC}"; }
warn()  { echo "${YEL}! $*${NC}"; }
info()  { echo "${BLU}==> $*${NC}"; }

# ---------- 参数解析 ----------
SKIP_INSTALL=0
ONLY_APPS=0
DRY_RUN=0
for a in "$@"; do
  case "$a" in
    --skip-install) SKIP_INSTALL=1 ;;
    --only-apps)    ONLY_APPS=1; SKIP_INSTALL=1 ;;
    --dry-run)      DRY_RUN=1 ;;
    -h|--help)      sed -n '2,30p' "$0"; exit 0 ;;
    *) err "未知参数：$a"; exit 2 ;;
  esac
done

run() {
  if (( DRY_RUN )); then
    echo "  [dry-run] $*"
  else
    eval "$@"
  fi
}

# ---------- 1. 加载配置 ----------
CONF="$SCRIPT_DIR/deploy.conf"
if [[ ! -f "$CONF" ]]; then
  err "缺少配置文件：$CONF"
  echo "  执行：cp $SCRIPT_DIR/deploy.conf.example $CONF && vim $CONF"
  exit 1
fi
# shellcheck disable=SC1090
set -a; source "$CONF"; set +a

MISSING=()
[[ -z "${ACR_REGISTRY:-}"     ]] && MISSING+=("ACR_REGISTRY")
[[ -z "${ACR_REGISTRY_VPC:-}" ]] && MISSING+=("ACR_REGISTRY_VPC")
[[ -z "${ACR_NAMESPACE:-}"    ]] && MISSING+=("ACR_NAMESPACE")
[[ -z "${ACR_USERNAME:-}"     ]] && MISSING+=("ACR_USERNAME")
[[ -z "${ACR_PASSWORD:-}"     ]] && MISSING+=("ACR_PASSWORD")
[[ -z "${IMAGE_TAG:-}"        ]] && MISSING+=("IMAGE_TAG")
[[ -z "${LLM_IMAGE:-}"        ]] && MISSING+=("LLM_IMAGE")
[[ -z "${APP_ENV_FILE:-}"     ]] && MISSING+=("APP_ENV_FILE")

if (( ${#MISSING[@]} )); then
  err "deploy.conf 缺少必填项："
  printf '    - %s\n' "${MISSING[@]}"
  exit 1
fi

if (( ! ONLY_APPS )) && [[ ! -f "$APP_ENV_FILE" ]]; then
  err "业务密钥文件不存在：$APP_ENV_FILE"
  echo "  参考 docs/02-部署实施.md §6 准备，或将 APP_ENV_FILE 改指到已有文件"
  exit 1
fi

# ---------- 2. root 检查 ----------
if [[ $EUID -ne 0 ]] && (( ! DRY_RUN )); then
  err "本脚本需要 root 权限（要写 /etc/rancher、装 systemd 服务）"
  echo "  执行：sudo bash $0 $*"
  exit 1
fi

API_IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/api:${IMAGE_TAG}"
WEB_IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/web:${IMAGE_TAG}"

info "部署参数"
cat <<EOF
  API_IMAGE            = $API_IMAGE
  WEB_IMAGE            = $WEB_IMAGE
  LLM_IMAGE            = $LLM_IMAGE
  ACR_REGISTRY (VPC)   = $ACR_REGISTRY_VPC
  APP_ENV_FILE         = $APP_ENV_FILE
  RUN_MIGRATION        = ${RUN_MIGRATION:-false}
  WEB_EXPOSE           = ${WEB_EXPOSE:-nodeport}
  ENABLE_NETWORKPOLICY = ${ENABLE_NETWORKPOLICY:-true}
  DRY_RUN              = $DRY_RUN
EOF
echo

# ==========================================================
# 阶段 1：安装 k3s
# ==========================================================
if (( ! SKIP_INSTALL )); then
  if command -v k3s >/dev/null 2>&1; then
    ok "k3s 已安装，跳过安装步骤（用 --skip-install 也能跳过）"
  else
    info "阶段 1/7：安装 k3s（走国内镜像加速）"
    run "curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | \
         INSTALL_K3S_MIRROR=cn \
         INSTALL_K3S_EXEC='--disable=traefik --write-kubeconfig-mode=644' \
         sh -"
    ok "k3s 已安装"
  fi

  # 等待 API server 就绪
  info "等待 k3s API server 就绪..."
  for i in $(seq 1 30); do
    if (( DRY_RUN )) || kubectl get --raw='/readyz' >/dev/null 2>&1; then
      ok "k3s API server 已就绪"
      break
    fi
    sleep 2
    if [[ $i == 30 ]]; then
      err "k3s API server 30 秒内未就绪，请检查：journalctl -u k3s -n 100"
      exit 1
    fi
  done
fi

# 让 kubectl 用 k3s 的 kubeconfig
export KUBECONFIG="/etc/rancher/k3s/k3s.yaml"

# ==========================================================
# 阶段 2：配置 ACR 免密拉取
# ==========================================================
if (( ! ONLY_APPS )); then
  info "阶段 2/7：配置 containerd registries.yaml（ACR 免密 + VPC 内网）"
  REG_FILE="/etc/rancher/k3s/registries.yaml"
  if [[ -f "$REG_FILE" ]] && grep -q "$ACR_REGISTRY_VPC" "$REG_FILE" 2>/dev/null; then
    ok "$REG_FILE 已配置 $ACR_REGISTRY_VPC，跳过"
  else
    if (( DRY_RUN )); then
      echo "  [dry-run] 写入 $REG_FILE"
    else
      mkdir -p /etc/rancher/k3s
      cat > "$REG_FILE" <<EOF
mirrors:
  ${ACR_REGISTRY}:
    endpoint:
      - "https://${ACR_REGISTRY_VPC}"
configs:
  ${ACR_REGISTRY_VPC}:
    auth:
      username: "${ACR_USERNAME}"
      password: "${ACR_PASSWORD}"
EOF
      chmod 600 "$REG_FILE"
    fi
    ok "$REG_FILE 已写入，重启 k3s 使配置生效"
    run "systemctl restart k3s"
    for i in $(seq 1 30); do
      if (( DRY_RUN )) || kubectl get --raw='/readyz' >/dev/null 2>&1; then break; fi
      sleep 2
    done
  fi
fi

# ==========================================================
# 阶段 3：建 namespace
# ==========================================================
info "阶段 3/7：建 namespace venus-prod / llm-prod"
for ns in venus-prod llm-prod; do
  if (( DRY_RUN )); then
    echo "  [dry-run] kubectl create namespace $ns（若不存在）"
  else
    kubectl get ns "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
  fi
done
ok "namespace 就绪"

# ==========================================================
# 阶段 4：导 Secret
# ==========================================================
info "阶段 4/7：导入 Secret"

# 业务 Secret（从 APP_ENV_FILE 全量导入）
if (( DRY_RUN )); then
  echo "  [dry-run] kubectl -n venus-prod create secret generic api-secret --from-env-file=$APP_ENV_FILE"
else
  kubectl -n venus-prod create secret generic api-secret \
      --from-env-file="$APP_ENV_FILE" \
      --dry-run=client -o yaml | kubectl apply -f -
  ok "venus-prod/api-secret 已导入（源：$APP_ENV_FILE）"
fi

# LLM SERVICE_API_KEY（生成或复用现有）
if (( DRY_RUN )); then
  LLM_KEY="<will-be-generated>"
  echo "  [dry-run] 生成 LLM_SERVICE_API_KEY 并注入到 llm-prod/llm-secret + venus-prod/api-secret"
else
  if kubectl -n llm-prod get secret llm-secret >/dev/null 2>&1; then
    LLM_KEY=$(kubectl -n llm-prod get secret llm-secret -o jsonpath='{.data.SERVICE_API_KEY}' | base64 -d)
    ok "llm-prod/llm-secret 已存在，复用其中的 SERVICE_API_KEY"
  else
    LLM_KEY=$(openssl rand -hex 32)
    kubectl -n llm-prod create secret generic llm-secret \
        --from-literal=SERVICE_API_KEY="$LLM_KEY"
    ok "llm-prod/llm-secret 已创建（新生成 SERVICE_API_KEY）"
  fi

  # 把同一个 key 补进业务侧 Secret，供 api Pod 调模型时鉴权
  kubectl -n venus-prod patch secret api-secret \
      --patch="{\"stringData\":{\"LLM_SERVICE_API_KEY\":\"$LLM_KEY\"}}"
  ok "venus-prod/api-secret 已补入 LLM_SERVICE_API_KEY"
fi

# ==========================================================
# 阶段 5：部署业务（复用 infra/k8s/）
# ==========================================================
info "阶段 5/7：部署业务 Deployment / Service / ConfigMap"

K8S_DIR="$ROOT_DIR/infra/k8s"
[[ -d "$K8S_DIR" ]] || { err "找不到 $K8S_DIR"; exit 1; }

# ConfigMap
run "kubectl apply -f '$K8S_DIR/01-configmap.yaml'"

# Deployments / Services（用 sed 替换镜像 tag，避免依赖 kustomize）
for f in 10-api-deployment.yaml 11-api-service.yaml 12-api-hpa.yaml \
         20-web-deployment.yaml 21-web-service.yaml \
         30-cron-deployment.yaml; do
  path="$K8S_DIR/$f"
  [[ -f "$path" ]] || { warn "跳过不存在的文件：$f"; continue; }
  if (( DRY_RUN )); then
    echo "  [dry-run] sed 's|REPLACE_ME_SHA|$IMAGE_TAG|g' $path | kubectl apply -f -"
  else
    sed "s|REPLACE_ME_SHA|$IMAGE_TAG|g" "$path" | kubectl apply -f -
  fi
done
ok "业务资源已 apply"

# Web 暴露方式
if [[ "${WEB_EXPOSE:-nodeport}" == "nodeport" ]]; then
  info "  将 web Service 改为 NodePort（${WEB_NODEPORT_HTTP:-30080}/${WEB_NODEPORT_HTTPS:-30443}）"
  if (( DRY_RUN )); then
    echo "  [dry-run] kubectl -n venus-prod patch svc web ..."
  else
    kubectl -n venus-prod patch svc web --type=merge -p "$(cat <<EOF
{
  "spec": {
    "type": "NodePort",
    "ports": [
      {"name":"http","port":80,"targetPort":80,"nodePort":${WEB_NODEPORT_HTTP:-30080}},
      {"name":"https","port":443,"targetPort":443,"nodePort":${WEB_NODEPORT_HTTPS:-30443}}
    ]
  }
}
EOF
)"
  fi
fi

# ==========================================================
# 阶段 6：数据库迁移（可选）
# ==========================================================
if [[ "${RUN_MIGRATION:-false}" == "true" ]]; then
  info "阶段 6/7：执行 Alembic 数据库迁移"
  MIGRATE_NAME="migrate-$(date +%s)"
  MIGRATE_YAML=$(cat <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $MIGRATE_NAME
  namespace: venus-prod
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: Never
      imagePullSecrets:
        - name: acr-cred
      containers:
        - name: migrate
          image: $API_IMAGE
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: api-config
            - secretRef:
                name: api-secret
EOF
)
  if (( DRY_RUN )); then
    echo "  [dry-run] 提交迁移 Job：$MIGRATE_NAME"
  else
    echo "$MIGRATE_YAML" | kubectl apply -f -
    echo "  等待迁移完成（最多 5 分钟）..."
    if kubectl -n venus-prod wait --for=condition=complete --timeout=300s "job/$MIGRATE_NAME"; then
      ok "迁移成功"
      kubectl -n venus-prod logs "job/$MIGRATE_NAME" --tail=50
    else
      err "迁移失败或超时，查看日志："
      kubectl -n venus-prod logs "job/$MIGRATE_NAME" --tail=200
      exit 1
    fi
  fi
else
  info "阶段 6/7：跳过数据库迁移（deploy.conf 中 RUN_MIGRATION=false）"
fi

# ==========================================================
# 阶段 7：部署模型服务 + Service + NetworkPolicy
# ==========================================================
info "阶段 7/7：部署模型服务 llm-service"

GPU_LIMIT_LINE=""
if [[ "${LLM_GPU_COUNT:-0}" != "0" ]]; then
  GPU_LIMIT_LINE="              nvidia.com/gpu: \"${LLM_GPU_COUNT}\""
fi

LLM_DEPLOY_YAML=$(cat <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-service
  namespace: llm-prod
  labels:
    app: llm-service
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: llm-service
  template:
    metadata:
      labels:
        app: llm-service
    spec:
      imagePullSecrets:
        - name: acr-cred
      containers:
        - name: llm
          image: ${LLM_IMAGE}
          ports:
            - name: http
              containerPort: ${LLM_PORT:-8080}
          env:
            - name: SERVICE_API_KEY
              valueFrom:
                secretKeyRef:
                  name: llm-secret
                  key: SERVICE_API_KEY
          resources:
            requests:
              cpu: "${LLM_CPU_REQUEST:-1000m}"
              memory: "${LLM_MEM_REQUEST:-4Gi}"
            limits:
              cpu: "${LLM_CPU_LIMIT:-4000m}"
              memory: "${LLM_MEM_LIMIT:-8Gi}"
${GPU_LIMIT_LINE}
          readinessProbe:
            httpGet:
              path: ${LLM_HEALTH_PATH:-/health}
              port: ${LLM_PORT:-8080}
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 6
          livenessProbe:
            httpGet:
              path: ${LLM_HEALTH_PATH:-/health}
              port: ${LLM_PORT:-8080}
            initialDelaySeconds: 120
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: llm-service
  namespace: llm-prod
  labels:
    app: llm-service
spec:
  selector:
    app: llm-service
  ports:
    - name: http
      port: ${LLM_PORT:-8080}
      targetPort: ${LLM_PORT:-8080}
  type: ClusterIP
EOF
)

if (( DRY_RUN )); then
  echo "  [dry-run] 提交模型服务 Deployment + Service"
else
  echo "$LLM_DEPLOY_YAML" | kubectl apply -f -
  ok "模型服务已 apply"
fi

# NetworkPolicy：只允许 venus-prod/api 访问 llm-prod/llm-service
if [[ "${ENABLE_NETWORKPOLICY:-true}" == "true" ]]; then
  NP_YAML=$(cat <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-service-allow-api
  namespace: llm-prod
spec:
  podSelector:
    matchLabels:
      app: llm-service
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: venus-prod
          podSelector:
            matchLabels:
              app: api
      ports:
        - protocol: TCP
          port: ${LLM_PORT:-8080}
EOF
)
  if (( DRY_RUN )); then
    echo "  [dry-run] 提交 NetworkPolicy llm-service-allow-api"
  else
    echo "$NP_YAML" | kubectl apply -f -
    ok "NetworkPolicy 已启用（仅 venus-prod/api 可访问 llm-service:${LLM_PORT:-8080}）"
  fi
fi

# ==========================================================
# 收尾：等 Pod 就绪 + 打通性检查
# ==========================================================
if (( DRY_RUN )); then
  ok "dry-run 结束"
  exit 0
fi

info "等待关键 Deployment 就绪（最多 5 分钟）"
kubectl -n venus-prod rollout status deploy/api         --timeout=300s || warn "api 未在 5 分钟内就绪，查 logs"
kubectl -n venus-prod rollout status deploy/web         --timeout=300s || warn "web 未在 5 分钟内就绪，查 logs"
kubectl -n llm-prod   rollout status deploy/llm-service --timeout=300s || warn "llm-service 未在 5 分钟内就绪，查 logs"

info "打通性检查：从 api Pod 访问 llm-service"
if kubectl -n venus-prod exec deploy/api -- \
    curl -sfm 5 "http://llm-service.llm-prod.svc.cluster.local:${LLM_PORT:-8080}${LLM_HEALTH_PATH:-/health}" \
    >/dev/null; then
  ok "业务 → 模型服务连通性 OK"
else
  warn "业务 → 模型服务健康检查失败，可能原因："
  echo "    1. 模型服务还没完全加载（大模型加载几分钟很正常，稍后重试）"
  echo "    2. LLM_HEALTH_PATH（当前 ${LLM_HEALTH_PATH:-/health}）与模型服务实际路径不符"
  echo "    3. NetworkPolicy 把请求拦了 - 但 api Pod 标签必须包含 app=api"
  echo "  排查："
  echo "    kubectl -n llm-prod logs deploy/llm-service --tail=100"
  echo "    kubectl -n llm-prod get endpoints llm-service"
fi

echo
ok "部署完成 - 汇总"
kubectl get pods -A -o wide | grep -E 'venus-prod|llm-prod|NAME'
echo
kubectl -n venus-prod get svc
kubectl -n llm-prod get svc
echo

cat <<EOF

下一步：
  访问业务 Web（NodePort 模式）：http://<ECS 公网 IP>:${WEB_NODEPORT_HTTP:-30080}
                                  https://<ECS 公网 IP>:${WEB_NODEPORT_HTTPS:-30443}
  查看业务日志：      kubectl -n venus-prod logs -f deploy/api
  查看模型服务日志：  kubectl -n llm-prod   logs -f deploy/llm-service
  升级业务镜像 tag：  vim infra/k3s/deploy.conf 改 IMAGE_TAG，再跑：
                     sudo bash infra/k3s/deploy.sh --only-apps
  回滚业务：          kubectl -n venus-prod rollout undo deploy/api
  完整说明：          docs/references/DEPLOY_K3S.md
EOF
