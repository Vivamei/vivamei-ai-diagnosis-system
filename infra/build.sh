#!/usr/bin/env bash
# 一键打镜像：构建 api / web 两个镜像，并（可选）推送到阿里云 ACR。
#
# 非敏感配置(config/prod.baseline.env)会被烤进 api 镜像；密钥绝不入镜像，运行时由服务器
# /etc/venus-4s/.env 注入（详见 docs/部署文档-阿里云ECS.md）。
#
# 用法：
#   infra/build.sh                 # 只构建，本地打 tag
#   infra/build.sh --push          # 构建后登录 ACR 并推送（首次交互式输密码，之后自动免密）
#   infra/build.sh --push --relogin # 强制重新登录（凭证过期时用）
#   infra/build.sh --tag=v1.2.0 --push
#   IMAGE_TAG=v1.2.0 infra/build.sh --push
#
# 零交互推送（CI 或本地自动化用）：
#   ACR_USERNAME='ops@1234567890123456' ACR_PASSWORD='xxx' \
#       infra/build.sh --push
#   或把 ACR_USERNAME/ACR_PASSWORD 填到 infra/build.conf（记得 chmod 600）
#
# 登录逻辑（三级优先）：
#   1. 本机 ~/.docker/config.json 里已有 ACR 凭证 → 跳过 login（首次登录后终身免密，除非加 --relogin）
#   2. 提供了 ACR_USERNAME / ACR_PASSWORD → 走 docker login --password-stdin
#   3. 以上都没有 → 弹交互式 docker login 提示
#
# 构建参数来自 infra/build.conf（从 infra/build.conf.example 复制填写）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; NC=$'\033[0m'
err()  { echo "${RED}✗ $*${NC}" >&2; }
ok()   { echo "${GRN}✓ $*${NC}"; }
warn() { echo "${YEL}! $*${NC}"; }

MISSING=()

# ---------- 读取构建配置 ----------
BUILD_CONF="$ROOT_DIR/infra/build.conf"
if [[ ! -f "$BUILD_CONF" ]]; then
  err "缺少构建配置：infra/build.conf"
  echo "  先复制样例并填写 ACR 地址/命名空间："
  echo "    cp infra/build.conf.example infra/build.conf"
  exit 1
fi
set -a; source "$BUILD_CONF"; set +a

ACR_REGISTRY="${ACR_REGISTRY:-}"
ACR_NAMESPACE="${ACR_NAMESPACE:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

# ---------- 解析命令行参数 ----------
PUSH=0
FORCE_LOGIN=0
for a in "$@"; do
  case "$a" in
    --push)         PUSH=1 ;;
    --relogin)      FORCE_LOGIN=1 ;;
    --tag=*)        IMAGE_TAG="${a#*=}" ;;
    --platform=*)   PLATFORM="${a#*=}" ;;
    -h|--help)      sed -n '2,20p' "$0"; exit 0 ;;
    *) err "未知参数：$a（可用：--push --relogin --tag=X --platform=X）"; exit 2 ;;
  esac
done

# ---------- 校验构建参数 ----------
[[ -z "$ACR_REGISTRY"  ]] && MISSING+=("build.conf: ACR_REGISTRY  (如 registry.cn-hangzhou.aliyuncs.com)")
[[ -z "$ACR_NAMESPACE" ]] && MISSING+=("build.conf: ACR_NAMESPACE (ACR 命名空间，如 venus)")
[[ -z "$IMAGE_TAG"     ]] && MISSING+=("IMAGE_TAG 为空（build.conf 或 --tag= 指定）")

# ---------- 校验烤进镜像的应用配置 ----------
APP_CONF="$ROOT_DIR/config/prod.baseline.env"
if [[ ! -f "$APP_CONF" ]]; then
  MISSING+=("config/prod.baseline.env  (烤进 api 镜像的非敏感配置，缺失)")
else
  for k in APP_ENV LLM_PROVIDER; do
    grep -Eq "^${k}=" "$APP_CONF" || MISSING+=("prod.baseline.env 缺少必填项 ${k}")
  done

  # 严禁把密钥烤进镜像（推到 ACR 等于泄露，能解开所有加密手机号）
  LEAKED=()
  for k in DATABASE_URL REDIS_URL JWT_SECRET PHONE_DEK_BASE64 PHONE_HMAC_KEY \
           ALI_ACCESS_KEY_ID ALI_ACCESS_KEY_SECRET ADMIN_TOKEN WX_SECRET; do
    grep -Eq "^${k}=." "$APP_CONF" && LEAKED+=("$k")
  done
  if (( ${#LEAKED[@]} )); then
    err "config/prod.baseline.env 里出现了密钥，禁止烤进镜像："
    printf '    - %s\n' "${LEAKED[@]}"
    echo "  这些必须放到服务器 /etc/venus-4s/.env（运行时注入），不能进镜像。"
    exit 1
  fi

  # 占位符仅告警，不阻断
  if grep -Eq 'your-domain\.com|REPLACE|<账号ID>|your-llm-endpoint' "$APP_CONF"; then
    warn "prod.baseline.env 仍含占位符（your-domain.com / <账号ID> / your-llm-endpoint 等），确认是否要改成真实值再构建。"
  fi
fi

# ---------- 前置依赖检查 ----------
command -v docker >/dev/null 2>&1 || MISSING+=("docker 未安装或不在 PATH")
command -v node   >/dev/null 2>&1 || MISSING+=("node 未安装或不在 PATH（生成前端 .env 需要）")
[[ -f "$ROOT_DIR/config/frontend.env" ]]  || MISSING+=("config/frontend.env  (前端配置唯一真源，缺失)")
[[ -f "$ROOT_DIR/pnpm-lock.yaml" ]]       || MISSING+=("pnpm-lock.yaml  (web 镜像 --frozen-lockfile 需要)")
[[ -f "$ROOT_DIR/apps/api/poetry.lock" ]] || MISSING+=("apps/api/poetry.lock")
[[ -f "$ROOT_DIR/apps/api/Dockerfile" ]]  || MISSING+=("apps/api/Dockerfile")
[[ -f "$ROOT_DIR/apps/web/Dockerfile" ]]  || MISSING+=("apps/web/Dockerfile")

# ---------- 缺失则统一提示 ----------
if (( ${#MISSING[@]} )); then
  err "配置/依赖缺失，无法打镜像，请补齐后重试："
  printf '    - %s\n' "${MISSING[@]}"
  echo
  echo "  构建参数：infra/build.conf         （从 build.conf.example 复制）"
  echo "  镜像配置：config/prod.baseline.env （非敏感项，会烤进 api 镜像）"
  echo "  运行密钥：服务器 /etc/venus-4s/.env （不入镜像）"
  exit 1
fi

API_IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/api:${IMAGE_TAG}"
WEB_IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/web:${IMAGE_TAG}"

ok "校验通过，开始构建"
echo "  API_IMAGE = $API_IMAGE"
echo "  WEB_IMAGE = $WEB_IMAGE"
echo "  PLATFORM  = $PLATFORM"
echo

# ---------- 构建 ----------
# ---------- 生成前端 .env ----------
# apps/web/.env.production 由 config/frontend.env 生成，且必须在 docker build 之前生成好：
# Dockerfile 是 COPY apps/web 整个目录进构建上下文的，晚一步 Vite 就读不到。
echo "==> 生成前端 .env（来源 config/frontend.env）"
node "$ROOT_DIR/scripts/gen-frontend-env.mjs" web

echo "==> 构建 api 镜像"
docker build --platform "$PLATFORM" -f apps/api/Dockerfile -t "$API_IMAGE" .

echo "==> 构建 web 镜像"
docker build --platform "$PLATFORM" -f apps/web/Dockerfile -t "$WEB_IMAGE" .

ok "镜像构建完成"

# ---------- 推送 ----------
if (( PUSH )); then
  ACR_USERNAME="${ACR_USERNAME:-}"
  ACR_PASSWORD="${ACR_PASSWORD:-}"

  # 检查 ~/.docker/config.json 是否已有该 registry 的凭证缓存
  # （首次 docker login 后凭证会被 docker 缓存到本地，等效 gh CLI / git GCM 的免密体验）
  DOCKER_CFG="${DOCKER_CONFIG:-$HOME/.docker}/config.json"
  ALREADY_LOGGED_IN=0
  if [[ -f "$DOCKER_CFG" ]]; then
    if command -v jq >/dev/null 2>&1; then
      jq -e --arg r "$ACR_REGISTRY" '.auths[$r] != null' "$DOCKER_CFG" >/dev/null 2>&1 && ALREADY_LOGGED_IN=1
    else
      # 无 jq 就退回到简单字符串匹配，够用
      grep -Fq "\"$ACR_REGISTRY\"" "$DOCKER_CFG" && ALREADY_LOGGED_IN=1
    fi
  fi

  if (( ALREADY_LOGGED_IN )) && (( ! FORCE_LOGIN )); then
    ok "$ACR_REGISTRY 已有本地凭证缓存（$DOCKER_CFG），跳过 docker login"
    echo "    如需强制重新登录（凭证过期时）：加 --relogin"
  elif [[ -n "$ACR_USERNAME" && -n "$ACR_PASSWORD" ]]; then
    echo "==> 登录 ACR：$ACR_REGISTRY（非交互，来自环境变量 / build.conf）"
    # --password-stdin 避免密码进入 ps 输出或 shell 历史
    printf '%s' "$ACR_PASSWORD" | \
        docker login "$ACR_REGISTRY" --username "$ACR_USERNAME" --password-stdin
  else
    echo "==> 登录 ACR：$ACR_REGISTRY（交互式）"
    echo "    如需零交互推送，请在 build.conf 或环境变量里设 ACR_USERNAME / ACR_PASSWORD"
    docker login "$ACR_REGISTRY"
  fi

  echo "==> 推送 api"; docker push "$API_IMAGE"
  echo "==> 推送 web"; docker push "$WEB_IMAGE"
  ok "推送完成"
else
  warn "本地构建完成，未推送（加 --push 可推到 ACR）"
fi

cat <<EOF

下一步（在 ECS 上部署）：
  export API_IMAGE=$API_IMAGE
  export WEB_IMAGE=$WEB_IMAGE
  docker compose -f infra/docker-compose.ecs.yml pull
  docker compose -f infra/docker-compose.ecs.yml up -d

运行时仍需在服务器 /etc/venus-4s/.env 提供这些密钥（不在镜像内）：
  DATABASE_URL  REDIS_URL  JWT_SECRET  PHONE_DEK_BASE64  PHONE_HMAC_KEY
  ALI_ACCESS_KEY_ID  ALI_ACCESS_KEY_SECRET  ADMIN_TOKEN
  WX_SECRET（小程序转正式后填；内测期留空走 mock）
EOF
