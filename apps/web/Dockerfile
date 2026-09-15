# ===== build stage =====
FROM node:20-alpine AS builder
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json* ./
COPY packages/shared-types ./packages/shared-types
COPY apps/web ./apps/web

RUN pnpm install --frozen-lockfile --filter @venus/web...
WORKDIR /app/apps/web
RUN pnpm build

# ===== runtime stage =====
FROM nginx:1.27-alpine
COPY infra/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -qO- http://localhost/healthz || exit 1
