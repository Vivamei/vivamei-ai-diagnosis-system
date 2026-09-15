#!/usr/bin/env bash
# scripts/gen-types.sh
# 从运行中的 FastAPI 拉 openapi.json，生成 TypeScript 类型到 packages/shared-types/api.ts
set -euo pipefail

API_URL="${API_URL:-http://localhost:8080/openapi.json}"
OUT="packages/shared-types/api.ts"

cd "$(dirname "$0")/.."
npx -y openapi-typescript "$API_URL" -o "$OUT"
echo "wrote $OUT"
