# 第 3 段：数据库 Schema（MySQL 8）

只建 6 张表，覆盖整个 4S H5 业务闭环。所有表都有 `created_at / updated_at`，DELETE 一律软删（`deleted_at`），便于事故追溯。

## 表结构

```sql
-- 1) 用户表（凭手机号唯一）
CREATE TABLE users (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  phone         VARCHAR(20)  NOT NULL,
  phone_hash    CHAR(64)     NOT NULL,        -- HMAC-SHA256(phone)，索引用
  nickname      VARCHAR(64)  NULL,
  consent_at    DATETIME     NOT NULL,        -- 首次同意隐私协议时间
  consent_ver   VARCHAR(16)  NOT NULL,        -- 协议版本号
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at    DATETIME     NULL,
  UNIQUE KEY uk_phone_hash (phone_hash),
  KEY idx_created (created_at)
) ENGINE=InnoDB;
-- phone 列加密存储（AES-256-GCM，KMS 管 KEK）。phone_hash 用于查找。

-- 2) 照片元数据
CREATE TABLE photos (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id         BIGINT UNSIGNED NULL,           -- 拍照时可能尚未登录
  oss_key         VARCHAR(255) NOT NULL,          -- OSS 内部 key（非公网 URL）
  width           INT  NULL,
  height          INT  NULL,
  bytes           INT  NULL,
  mime            VARCHAR(32) NULL,
  client_ip       VARCHAR(45) NULL,               -- IPv6 兼容
  moderation_status ENUM('pending','passed','rejected') NOT NULL DEFAULT 'pending',
  moderation_raw  JSON NULL,                      -- 阿里云返回原始结果
  expires_at      DATETIME NOT NULL,              -- 10 天后过期（合规要求）
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at      DATETIME NULL,
  KEY idx_user (user_id),
  KEY idx_expires (expires_at)
) ENGINE=InnoDB;

-- 3) 分析任务（一次拍照触发一个 task）
CREATE TABLE analysis_tasks (
  id             CHAR(26)     PRIMARY KEY,         -- ULID（前端 URL 也用它）
  user_id        BIGINT UNSIGNED NULL,
  photo_id       BIGINT UNSIGNED NOT NULL,
  status         ENUM('queued','streaming','done','failed','moderated_out')
                 NOT NULL DEFAULT 'queued',
  llm_provider   VARCHAR(32)  NOT NULL,            -- 'qwen-vl' 等，便于切换追溯
  llm_request    JSON         NULL,                -- 发给 LLM 的 payload(摘要)
  error_code     VARCHAR(64)  NULL,
  error_message  TEXT         NULL,
  started_at     DATETIME     NULL,
  finished_at    DATETIME     NULL,
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user (user_id),
  KEY idx_status_created (status, created_at)
) ENGINE=InnoDB;

-- 4) 4S 报告（与 task 一对一；落库便于复看/导出长图）
CREATE TABLE reports (
  id             BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  task_id        CHAR(26)     NOT NULL,
  schema_version VARCHAR(8)   NOT NULL DEFAULT 'v1',   -- 与 LLM schema 对齐
  stype          JSON NOT NULL,   -- 分相
  style          JSON NOT NULL,   -- 分型
  subzone        JSON NOT NULL,   -- 分区
  struct_        JSON NOT NULL,   -- 分层（DB 列名加下划线避免 SQL 保留字；
                                  --  对外 LLMEvent.phase 与 JSON key 仍用裸 "struct"）
  radar_scores   JSON NOT NULL,   -- {stype:78, style:82, subzone:74, struct:69}
  optimization   TEXT NOT NULL,   -- 美学优化方向（文字）
  full_text      MEDIUMTEXT NOT NULL,  -- 流式输出拼接完成的全文（兜底/SEO）
  moderation_status ENUM('pending','passed','rejected') NOT NULL DEFAULT 'pending',
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_task (task_id)
) ENGINE=InnoDB;

-- 5) 留资 / 预约
CREATE TABLE bookings (
  id             BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id        BIGINT UNSIGNED NOT NULL,
  task_id        CHAR(26)     NULL,               -- 从哪份报告点过来的
  name           VARCHAR(64)  NOT NULL,
  phone          VARCHAR(20)  NOT NULL,           -- 同 users 表加密
  phone_hash     CHAR(64)     NOT NULL,
  store_code     VARCHAR(32)  NULL,               -- 门店编码
  appointment_at DATETIME     NULL,               -- 期望到店时间
  remark         VARCHAR(255) NULL,
  status         ENUM('new','contacted','arrived','closed') NOT NULL DEFAULT 'new',
  source         VARCHAR(32)  NULL,               -- utm/扫码点位等
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_user (user_id),
  KEY idx_status_created (status, created_at)
) ENGINE=InnoDB;

-- 6) 审计日志（合规留痕，6 个月以上）
CREATE TABLE audit_logs (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  actor_id    BIGINT UNSIGNED NULL,
  actor_ip    VARCHAR(45)   NULL,
  action      VARCHAR(64)   NOT NULL,             -- 'sms.send'/'report.view'/'photo.delete'...
  target_type VARCHAR(32)   NULL,
  target_id   VARCHAR(64)   NULL,
  meta        JSON          NULL,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_action_created (action, created_at)
) ENGINE=InnoDB;
```

## Redis Key 约定

| Key | TTL | 用途 |
|---|---|---|
| `sms:code:{phone_hash}` | 5 min | 短信验证码 |
| `sms:send:{phone_hash}` | 1 min | 防 60s 内重复发送 |
| `rl:ip:{ip}:{api}` | 1 min | IP 维度接口限流 |
| `rl:phone:{phone_hash}:analyze` | 1 day | 单手机号每日分析次数（防刷 AI 成本） |
| `task:stream:{task_id}` | 30 min | SSE 流式缓冲（断线重连续传） |
| `task:cursor:{task_id}` | 30 min | SSE 推送游标（Last-Event-ID） |

## 关键决策

- **手机号双列存储**：明文加密列 `phone` + HMAC 列 `phone_hash`。所有查找走 `phone_hash`，避免明文索引；明文用 KMS 管的密钥 AES-GCM 加密
- **报告 4 个维度各自 JSON 列而非一个大 JSON**：写性能差不多但读起来直观，未来加索引/统计也方便
- **`schema_version` 字段**：LLM 输出 schema 升级时（v1→v2 加字段），老报告还能正确解析
- **照片 10 天自动过期**：CRON 扫 `expires_at`，删 OSS 对象 + 软删行（与合规清单 R9 对齐）
- **没有 sessions 表**：JWT 自包含（access 1h + refresh 7d），refresh 黑名单走 Redis
