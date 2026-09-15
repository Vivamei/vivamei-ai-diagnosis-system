#!/usr/bin/env bash
# scripts/backup.sh
# 每日 03:00 由 cron 调用，备份 MySQL + Redis 到本地目录并加密上传 OSS。
# 需要环境变量：BACKUP_GPG_PASS、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE
set -euo pipefail

TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR="${BACKUP_DIR:-/var/venus-backups}"
mkdir -p "$BACKUP_DIR"

DB_USER="${MYSQL_USER:-venus}"
DB_PASS="${MYSQL_PASSWORD:?MYSQL_PASSWORD not set}"
DB_NAME="${MYSQL_DATABASE:-venus}"
GPG_PASS="${BACKUP_GPG_PASS:?BACKUP_GPG_PASS not set}"

echo "[backup] $TS — dump mysql"
mysqldump --single-transaction --routines --triggers \
  -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
  | gzip \
  | gpg --batch --symmetric --passphrase "$GPG_PASS" \
        -o "$BACKUP_DIR/db-$TS.sql.gz.gpg"

echo "[backup] $TS — redis BGSAVE"
docker exec venus-4s-redis-1 redis-cli BGSAVE
sleep 5
docker cp venus-4s-redis-1:/data/dump.rdb "$BACKUP_DIR/redis-$TS.rdb"
gpg --batch --symmetric --passphrase "$GPG_PASS" \
    -o "$BACKUP_DIR/redis-$TS.rdb.gpg" "$BACKUP_DIR/redis-$TS.rdb"
rm "$BACKUP_DIR/redis-$TS.rdb"

# OSS 上传（部署后启用）
# ossutil cp "$BACKUP_DIR/db-$TS.sql.gz.gpg" oss://venus-backups/db/
# ossutil cp "$BACKUP_DIR/redis-$TS.rdb.gpg" oss://venus-backups/redis/

# 保留 30 天
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "[backup] $TS done"
