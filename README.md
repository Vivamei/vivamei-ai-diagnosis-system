# AI 4S 美学顾问 Prompt 实现版

这个版本用于验证甲方最新需求：

> 上传人脸照片 → 基础质检 → 调用多模态大模型 → 输出结构化 4S 美学报告 → 合规过滤 → 生成 4S 雷达图数据 → 项目方向映射 → 返回前端 JSON

## 4S 输出内容

- **Stype 分相**：骨相主导 / 肉相主导 / 皮相主导 / 复合型
- **Style 分型**：华丽高雅 / 浪漫性感 / 魅力时尚 / 飒爽前卫 / 甜美少女 / 温婉柔美 / 盐系柔美 / 知性沉着 / 自然优雅
- **Subzone 分区**：额部、眉眼、中面部、鼻部、唇部、下颌轮廓
- **Struct 分层**：皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层
- **4S 雷达图**：`radar_chart.labels` + `radar_chart.values`
- **美学优化方向**：文字版方向建议，不输出具体医美项目

## 运行

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

打开：

```text
http://127.0.0.1:8000/docs
```

## V3：200 人高频访问的排队方案

V3 默认将 `/api/analyze-file` 和 `/api/analyze-url` 置为 `mode=queue`：接口只负责上传、准入和入队，立即返回 HTTP `202`，避免 200 个用户同时等待大模型而耗尽 API 进程。前端使用 `poll_url` 轮询结果。

```json
{
  "success": true,
  "status": "QUEUED",
  "job_id": "<job_id>",
  "poll_url": "/api/analysis-jobs/<job_id>"
}
```

查询接口：`GET /api/analysis-jobs/{job_id}`，状态为 `QUEUED`、`RUNNING`、`SUCCESS` 或 `FAILURE`。历史 `mode=sync`、`mode=async` 保留给联调，不应作为线上默认调用方式。

默认保护参数如下，可在 `.env` 调整：

| 项目 | 默认值 | 作用 |
|---|---:|---|
| 同一登录用户提交频率 | 5 次/分钟 | 第 6 次及之后返回 `429 USER_RATE_LIMITED`，带 `Retry-After` |
| 同一登录用户在途任务 | 5 个 | 超过后返回 `429 USER_QUEUE_LIMITED` |
| 同 IP 提交频率（兜底） | 300 次/分钟 | 防止单个网络来源异常刷接口；超过后返回 `429 IP_RATE_LIMITED` |
| 同 IP 在途任务（兜底） | 300 个 | 超过后返回 `429 IP_QUEUE_LIMITED` |
| 全局等待队列 | 500 个 | 队列满时返回 `503 QUEUE_FULL` |
| 实际模型分析并发 | 10 个 | Redis 分布式租约保证所有 Worker 合计不超过该数 |
| 结果与任务标记保留 | 24 小时 | 过期后查询返回 `404 JOB_NOT_FOUND` |


每个分析任务会调用多次大模型。若平均每个任务耗时 30 秒，模型并发 10 约能完成 20 个任务/分钟，200 个任务约需 10 分钟；若业务目标是约 5 分钟，需要将 `QUEUE_GLOBAL_MAX_INFLIGHT` 提升至约 20，并先确认模型账户并发配额与 ECS 出网能力。

部署：

```bash
docker compose up -d --build
docker compose ps
```


## .env 示例

```env
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=sk-ws-你的key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.7-plus

ARK_API_KEY=
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=

PUBLIC_BASE_URL=
HOST=0.0.0.0
PORT=8000
```


## 当前版本边界

本版本已经完成 4S 报告结构和雷达图数据输出，但仍是 Prompt 版：

- 人脸质量检测仍是基础图片格式/分辨率检查；正式上线建议接入腾讯云/百度人脸检测或 MediaPipe。
- OSS 上传和临时 URL 生成尚未内置；正式上线应将本地图片上传到 OSS，生成临时 URL，再调用模型，分析后删除原图。
- 内容安全目前是本地敏感词规则；正式上线建议叠加内容安全 API 和人工审核。

## 九型分相与专属建议

- 最终报告的 `report.stype.style_reference` 返回当前 Style 对应的固定皮相、肉相、骨相星级与分型原则。
- `report.stype.label` 和 `aging_signals` 表示照片当前可见状态；`style_reference` 表示该气质类型的审美参考，两者不要混用。
- 同步和异步模式都先确定最终 Style，再使用该型知识生成分相、分区、分层和优化建议。
- 优化建议按“分型专属方向 + 照片低分区域”生成，并保持非医疗、中性表达。

## LLM 错误码与重试

接口失败时保留原有顶层 `message`，并新增稳定结构：

```json
{
  "success": false,
  "error": {
    "code": "LLM_BILLING_ERROR",
    "message": "大模型账户状态异常，请联系管理员检查余额或服务状态。",
    "retryable": false,
    "request_id": "用于服务端日志排查的请求标识"
  },
  "message": "大模型账户状态异常，请联系管理员检查余额或服务状态。"
}
```

| 错误码 | 含义 | HTTP | 建议重试 |
|---|---|---:|---|
| `LLM_BILLING_ERROR` | API 欠费或账户状态异常 | 503 | 否，先处理余额或账户状态 |
| `LLM_AUTH_ERROR` | API Key 无效或无权限 | 503 | 否，先检查密钥和权限 |
| `LLM_MODEL_ERROR` | 模型名错误、模型未开通或无权限 | 503 | 否，先检查模型配置 |
| `LLM_RATE_LIMITED` | 上游 429 限流 | 503 | 是 |
| `LLM_TIMEOUT` | 连接或读取超时 | 504 | 是 |
| `LLM_UPSTREAM_UNAVAILABLE` | 上游 502/503/504、连接重置 | 503 | 是 |
| `LLM_IMAGE_UNAVAILABLE` | 模型侧无法下载图片 | 422 | 否，重新上传并检查图片公网权限 |
| `LLM_BAD_REQUEST` | 参数被上游拒绝 | 422 | 否，先修正请求或图片 |
| `LLM_INVALID_RESPONSE` | 模型输出不是完整合法 JSON | 502 | 是 |
| `CONFIG_ERROR` | 本地环境变量不完整 | 500 | 否，先检查 ECS `.env` |

服务端会对 429、超时、上游 502/503/504 等瞬态错误自动再试 1 次；总调用尝试次数最多 2 次。欠费、鉴权、模型配置和固定图片不可访问不会盲目重试。

## ECS 端口与故障排查

链路涉及的端口：

- 客户端直连 FastAPI：ECS 入站 TCP `8000`。
- 如果使用 Nginx、负载均衡或域名 HTTPS：ECS/负载均衡入站 `80/443`，再转发到本机 `8000`。
- ECS 调用阿里云 OSS：出站 HTTPS `443`。
- ECS 调用阿里云百炼或火山方舟：出站 HTTPS `443`。

建议按以下顺序排查：

1. `GET /health` 是否返回 200；若不通，检查进程、Docker、ECS 安全组和 `8000`/反向代理端口。
2. 查看错误响应中的 `error.code` 和 `request_id`，再按 request ID 查服务端日志。
3. `LLM_BILLING_ERROR` 检查云平台余额与账户状态；重试不能解决欠费。
4. `LLM_AUTH_ERROR` / `LLM_MODEL_ERROR` 检查 API Key、模型名称、开通区域与权限。
5. `LLM_IMAGE_UNAVAILABLE` 检查 OSS 对象是否能从公网访问、URL 是否过期、模型服务是否能访问该域名。
6. `LLM_RATE_LIMITED` / `LLM_TIMEOUT` / `LLM_UPSTREAM_UNAVAILABLE` 可稍后重试，并检查上游状态与 ECS 出站网络。
7. `LLM_INVALID_RESPONSE` 通常是模型输出被截断或格式漂移，可重试；持续出现时检查 token 预算与模型兼容性。

## 分析次数限制

当前后端没有“每小时 3 次 / 每天 5 次”的分析次数限制。线上默认的 `mode=queue` 使用 Redis 实施“每个登录用户每分钟最多 5 次”的短时保护，并用同 IP 每分钟 300 次作为兜底；`mode=sync` 和 `mode=async` 不走该队列准入。`eval_stage1.py --retries=2` 只是离线评测单条失败后的重试次数，与用户分析额度无关。

如果线上页面仍显示 hour/day 上限，需要检查不在本目录中的前端代码、Nginx/API 网关、云 WAF、Redis 用户服务或 ECS 上运行的其他部署版本。



{
  "success": false,
  "message": "报告命中敏感词，建议进入人工审核或重新生成。",
  "safety": {
    "hit_words": [
      "填充"
    ]
  }
}
