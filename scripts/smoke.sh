#!/usr/bin/env bash
# scripts/smoke.sh
# 部署后跑：HOST=https://your-domain bash scripts/smoke.sh
# 用 5 个最少 curl 验证全链路关键路径
set -euo pipefail
HOST="${HOST:-http://localhost:8080}"

echo "[1/5] /health"
curl -sf "$HOST/health" | grep -q '"status":"ok"'

echo "[2/5] openapi.json reachable"
curl -sf "$HOST/openapi.json" >/dev/null

echo "[3/5] /api/auth/sms/send returns 429 on rapid repeat"
PHONE="13099990000"
curl -sf -X POST "$HOST/api/auth/sms/send" \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"$PHONE\",\"scene\":\"login\"}" >/dev/null || true
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HOST/api/auth/sms/send" \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"$PHONE\",\"scene\":\"login\"}")
if [ "$CODE" != "429" ]; then
  echo "    expected 429, got $CODE"
  exit 1
fi

echo "[4/5] /api/auth/sms/verify with bad code returns 400"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HOST/api/auth/sms/verify" \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"$PHONE\",\"code\":\"000000\",\"consentVer\":\"v1.0\"}")
if [ "$CODE" != "400" ]; then
  echo "    expected 400, got $CODE"
  exit 1
fi

echo "[5/5] static index reachable"
curl -sfI "$HOST/" | head -1 | grep -q 200

echo "smoke OK"
