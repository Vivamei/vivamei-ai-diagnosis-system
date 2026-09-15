#!/usr/bin/env bash
# gh-link.sh — 把当前目录关联到 GitHub 上已建好的 repo。
# 只做关联(git init + 生成 .gitignore + 添加 remote),不 commit 也不 push。
# 后续 commit / push 由用户手动执行。
#
# 用法:
#   在任意项目目录下(如 cd /path/to/your-project)执行:
#     bash /path/to/gh-link.sh
#   或复制本脚本到项目目录内直接执行:
#     bash gh-link.sh
#   或放到 PATH(例如 ~/bin/gh-link)后全局使用:
#     gh-link
#
# 通用性:脚本不假设任何项目类型,可用于 Node / Python / Go / Rust / 纯静态站点等。

set -euo pipefail

# ---- 颜色输出 ----
if [[ -t 1 ]]; then
  RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; CYA=$'\033[36m'; NC=$'\033[0m'
else
  RED=''; GRN=''; YEL=''; CYA=''; NC=''
fi
info()  { echo "${CYA}▸ $*${NC}"; }
ok()    { echo "${GRN}✓ $*${NC}"; }
warn()  { echo "${YEL}! $*${NC}"; }
err()   { echo "${RED}✗ $*${NC}" >&2; }

# ---- 前置检查 ----
command -v git >/dev/null 2>&1 || { err "未找到 git,请先安装 Git"; exit 1; }

PROJECT_DIR="$(pwd)"
info "工作目录:$PROJECT_DIR"

# ---- 1. git init ----
if [[ ! -d .git ]]; then
  info "当前目录未初始化 git,执行 git init"
  git init -q
  # git 2.28+ 支持 -b main;旧版用 branch -M 兜底
  git symbolic-ref HEAD refs/heads/main 2>/dev/null || \
    git branch -M main 2>/dev/null || true
  ok "git 已初始化,当前分支 $(git branch --show-current 2>/dev/null || echo main)"
else
  current_branch="$(git branch --show-current 2>/dev/null || echo '(detached)')"
  ok "git 已初始化,当前分支 $current_branch"
fi

# ---- 2. 生成通用 .gitignore(仅当不存在时) ----
if [[ ! -f .gitignore ]]; then
  info "未找到 .gitignore,生成通用版"
  cat > .gitignore <<'GITIGNORE'
# ---- Node / TypeScript ----
node_modules/
dist/
build/
.vite/
.next/
.nuxt/
*.tsbuildinfo
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# ---- Python ----
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
env/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.tox/
htmlcov/
.coverage
.coverage.*
*.egg-info/

# ---- 密钥与环境变量 ----
.env
.env.*
!.env.example
!.env.sample
*.pem
*.key
*.crt

# ---- 编辑器 / IDE ----
.vscode/
.idea/
*.swp
*.swo
*~

# ---- 操作系统 ----
.DS_Store
Thumbs.db
Desktop.ini

# ---- 日志与临时文件 ----
*.log
logs/
tmp/
temp/

# ---- 测试与覆盖率 ----
playwright-report/
test-results/
coverage/

# ---- 构建产物 ----
target/
out/

# ---- 大文件与本地缓存 ----
*.zip
*.tar.gz
*.7z
GITIGNORE
  ok "已生成 .gitignore"
else
  ok "已存在 .gitignore,跳过"
fi

# ---- 3. 配置 remote origin ----
if git remote get-url origin >/dev/null 2>&1; then
  existing="$(git remote get-url origin)"
  warn "已存在 remote origin:$existing"
  read -rp "是否替换为新 URL? [y/N]: " ans
  if [[ "$ans" =~ ^[yYsS]$ ]]; then
    read -rp "请输入新的 GitHub repo URL: " repo_url
    if [[ -z "$repo_url" ]]; then
      err "URL 为空,已取消替换"
      exit 1
    fi
    git remote set-url origin "$repo_url"
    ok "已替换 origin 为 $repo_url"
  else
    info "保留现有 origin"
  fi
else
  echo
  echo "请提供 GitHub repo URL,支持以下两种格式:"
  echo "  HTTPS:https://github.com/<user>/<repo>.git"
  echo "  SSH: git@github.com:<user>/<repo>.git"
  read -rp "GitHub repo URL: " repo_url
  if [[ -z "$repo_url" ]]; then
    err "URL 为空,退出"
    exit 1
  fi
  git remote add origin "$repo_url"
  ok "已添加 remote origin:$repo_url"
fi

# ---- 4. 提示 user.name / user.email 未配置 ----
if ! git config user.name >/dev/null 2>&1 || ! git config user.email >/dev/null 2>&1; then
  echo
  warn "当前仓库未配置 git user.name / user.email(全局也未配置)"
  echo "  建议执行以下命令(二选一):"
  echo "    # 仅当前仓库"
  echo "    git config user.name  \"Your Name\""
  echo "    git config user.email \"you@example.com\""
  echo "    # 或全局配置"
  echo "    git config --global user.name  \"Your Name\""
  echo "    git config --global user.email \"you@example.com\""
fi

# ---- 5. 完成提示 ----
current_branch="$(git branch --show-current 2>/dev/null || echo main)"

cat <<EOF

${GRN}✓ 关联完成${NC}

后续手动执行:
  git add .
  git commit -m "初始提交"
  git push -u origin ${current_branch}

首次 push 若远程已有内容(如 GitHub 建 repo 时自动生成的 README/LICENSE):
  git pull --rebase origin ${current_branch}
  # 若出现冲突,按提示解决后
  git rebase --continue
  git push -u origin ${current_branch}

如首次 push 遇到分支名不匹配(远程是 master 而本地是 main):
  git branch -M master   # 或改远程默认分支为 main
  git push -u origin master

EOF
