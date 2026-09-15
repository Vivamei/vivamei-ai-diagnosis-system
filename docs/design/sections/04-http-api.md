# 第 4 段：HTTP API 设计

10 个 REST 端点 + 1 个 SSE 端点，全部 `/api` 前缀。统一规则：JSON in / JSON out、错误用 `{code, message, requestId}`、需要登录的接口在 `Authorization: Bearer <jwt>`。

## 4.1 鉴权

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/sms/send` | 发短信验证码（限频 60s / IP+手机） |
| POST | `/api/auth/sms/verify` | 校验验证码，返 access+refresh JWT |
| POST | `/api/auth/refresh` | 刷新 access token |
| POST | `/api/auth/logout` | refresh 入 Redis 黑名单 |

```http
POST /api/auth/sms/send
{ "phone": "13800138000", "scene": "login" }
→ 200 { "expiresIn": 300 }

POST /api/auth/sms/verify
{ "phone": "13800138000", "code": "123456", "consentVer": "v1.0" }
→ 200 { "accessToken":"...", "refreshToken":"...", "expiresIn": 3600,
        "user": { "id": 123, "nickname": null } }
```

## 4.2 拍照与上传

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload/token` | 拿 OSS STS 直传凭证（含限定 key 前缀、5min 有效） |
| POST | `/api/photos` | 上传完成回调：登记 photo + 触发内容安全机审 |

```http
POST /api/upload/token
→ 200 {
  "ossEndpoint": "https://venus-prod.oss-cn-hangzhou.aliyuncs.com",
  "accessKeyId":"STS.xxx", "accessKeySecret":"xxx", "securityToken":"xxx",
  "expiration":"2026-06-29T08:05:00Z",
  "objectKey":"uploads/2026/06/29/{uuid}.jpg",   // 后端预生成，前端不许改
  "maxBytes": 5242880
}

POST /api/photos
{ "ossKey":"uploads/2026/06/29/abc.jpg", "width":1080, "height":1440, "bytes":823412 }
→ 200 { "photoId": 456, "moderationStatus":"pending" }
# 后端异步调阿里云内容安全，rejected 时下次 analyze 会失败
```

## 4.3 4S 分析（核心）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/analyze` | 创建分析任务（不阻塞，返回 taskId） |
| GET  | `/api/analyze/{taskId}/stream` | **SSE**，订阅四维流式输出 |
| GET  | `/api/reports/{taskId}` | 取完整报告（兜底/复看） |

```http
POST /api/analyze
{ "photoId": 456 }
→ 202 { "taskId": "01HW9...", "status":"queued" }
# 限流: 同手机号每日 5 次，命中返 429 + retryAfter

GET /api/analyze/01HW9.../stream   # SSE，Last-Event-ID 支持断线续传
event: phase        data: {"phase":"stype","label":"分相分析中"}
event: delta        data: {"phase":"stype","text":"骨相为主导..."}
event: phase_done   data: {"phase":"stype","payload":{...完整 stype JSON...}}
event: phase        data: {"phase":"style", ...}
...
event: radar        data: {"stype":78,"style":82,"subzone":74,"struct":69}
event: done         data: {"taskId":"01HW9...","reportId":789}
event: error        data: {"code":"LLM_TIMEOUT","message":"...","retryable":true}

GET /api/reports/01HW9...
→ 200 { "taskId":"...","schemaVersion":"v1",
        "stype":{...},"style":{...},"subzone":{...},"struct":{...},
        "radarScores":{...},"optimization":"...","createdAt":"..." }
```

**SSE 设计要点**：
- 后端用 `StreamingResponse` + `asyncio.Queue`，从 LLM 服务拉到一片 delta 就推一次
- 每条 `event` 都带 `id:`（用 ULID 或自增），前端断线后用 `Last-Event-ID` 续传
- Redis 缓存最近 30 分钟的事件流，再连可重放
- 心跳：30s 一次 `: ping`，过 Nginx 不被 idle timeout 切断（`proxy_read_timeout 3600`）

## 4.4 留资 / 预约

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/bookings` | 提交留资 |

```http
POST /api/bookings
{ "name":"张三","phone":"13800138000","storeCode":"SH01",
  "appointmentAt":"2026-07-02T14:00:00+08:00","taskId":"01HW9...",
  "source":"qrcode_xianxia" }
→ 201 { "bookingId": 111 }
```

## 4.5 横切：错误码与限流

**错误码（部分）**：

| code | HTTP | 说明 |
|---|---|---|
| `AUTH_SMS_TOO_FREQUENT` | 429 | 60s 内重复发送 |
| `AUTH_SMS_INVALID` | 400 | 验证码错/过期 |
| `UPLOAD_TOO_LARGE` | 413 | 超过 5MB |
| `PHOTO_MODERATION_REJECTED` | 422 | 内容安全拒绝 |
| `ANALYZE_RATE_LIMITED` | 429 | 当日分析次数超限 |
| `LLM_UNAVAILABLE` | 503 | LLM 服务不可用 |
| `LLM_TIMEOUT` | 504 | 流式超时 |
| `TASK_NOT_FOUND` | 404 | 任务不存在或已过期 |

**限流（Redis token bucket）**：
- `/api/auth/sms/send`：IP 每分钟 5 次，手机号每分钟 1 次、每天 10 次
- `/api/analyze`：登录用户每天 5 次、每小时 3 次
- 兜底：所有 `/api/*` IP 每秒 20 次
