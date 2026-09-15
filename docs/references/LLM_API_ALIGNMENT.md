# 4S 美学报告 — LLM 接口对齐文档

> **目的**：对齐 4S H5（本方）与 4S AI 美学报告大模型服务（贵方）之间的接口契约。
> **背景**：贵方提供的《4S AI 美学报告接口说明文档 v1.0》（以下简称"贵方 doc"）与本方已实现的调用契约存在多处差异，本文逐项列出并提出需贵方确认的问题，方便我们在动代码前对齐方案。
> **本方当前实现**：`apps/api/app/services/llm/{base.py, qwen.py}`、`apps/api/app/services/analyze_runner.py`、`apps/web/src/pages/Report.tsx`。

---

## 0. 一图看懂差异

| 维度 | 本方契约（已实现） | 贵方 doc | 差异级别 |
|---|---|---|---|
| 通信方式 | **SSE 流式** | **同步 HTTP**（5–30s 阻塞返回） | 🔴 根本性 |
| 接口路径 | `POST {LLM_BASE_URL}/v1/analyze` | `POST /analyze-url` / `POST /analyze-file` | 🔴 |
| 请求 body | camelCase + 流式契约字段 | snake_case + 单图字段 | 🔴 |
| 响应 schema | `LLMEvent` 序列（phase/delta/...） | 整体 JSON（`{success, report, radar_chart, ...}`） | 🔴 |
| 子字段命名 | 见下表 | 见下表 | 🟡 字段需映射 |
| 图片来源 | OSS **私有桶 + 签名 URL**（限时有效，带 query） | "公网可访问的人脸图片 URL" | 🟡 需贵方确认能吃签名 URL |
| 错误结构 | `{error:{code, message}}`（AppError 风格） | `{success:false, stage, message, ...}` | 🟡 |
| 多出来的字段 | 无 | `mapped_project_directions / lead_cta / disclaimer / safety / meta` | 🟢 用不到可忽略 |

---

## 1. 本方契约速览（贵方可不读代码）

我方后端已实现一层 `LLMProvider` 抽象，对贵方服务的期待如下（v1）：

### 1.1 请求

```http
POST {LLM_QWEN_BASE_URL}/v1/analyze
Content-Type: application/json
Accept: text/event-stream

{
  "schemaVersion": "v1",
  "taskId": "<ULID>",                 // 本方分配，回 SSE 时透传
  "imageUrl": "https://oss.xxx/...?Signature=...&Expires=...",
  "locale": "zh-CN",
  "userHints": null,                  // 预留：年龄段、肤况等
  "promptOverrides": null             // 预留：灰度/AB
}
```

### 1.2 响应：`text/event-stream`，每个事件 `data:` 行是一个 JSON

```typescript
type LLMEvent =
  | { type: "phase",      phase: "stype"|"style"|"subzone"|"struct" }
  | { type: "delta",      phase: "...", text: "增量文本" }
  | { type: "phase_done", phase: "...", payload: { /* 该维度结构化数据 */ } }
  | { type: "radar",      radar: { stype: 82, style: 88, subzone: 85, struct: 80 } }
  | { type: "done",       payload: { optimization: "美学优化方向（一段话）" } }
  | { type: "error",      error: { code: "LLM_TIMEOUT", message: "...", retryable: true } }
```

设计动机：
- 流式 UX：前端要做"4 步进度 + 维度卡片逐字打出"，对应贵方 doc §21 的体验，但**真流式**优于假进度。
- 渐进合规：本方对每段 `delta` 做敏感词过滤，命中可立即中断并退回，避免完整等 30s 才发现违禁词。
- 与协议解耦：`LLMEvent` 是中间结构，未来换提供商不影响前端。

---

## 2. 差异详表 + 字段映射

### 2.1 stype（分相）

| 字段 | 贵方 doc | 本方期待（`phase_done.payload`） |
|---|---|---|
| 标签 | `label` | `label` ✅ |
| 分数 | `score` | （进 `radar.stype`） |
| 置信度 | `confidence` | 可选 `confidence` |
| 描述 | `description` | `narrative` ⚠️ 命名不同 |
| 证据 | `evidence[]` | `evidence[]` ✅ |

### 2.2 style（分型）

| 字段 | 贵方 doc | 本方期待 |
|---|---|---|
| 标签 | `label` | `primary_label` ⚠️ 命名不同 |
| 描述 | `description` | `narrative` ⚠️ |
| 关键词 | `keywords[]` | `keywords[]` ✅ |

### 2.3 subzone（分区）—— 命名差异最多

贵方 doc：
```json
{ "zones": [{ "zone": "额部", "status": "...", "strength": "...", "optimization": "..." }] }
```
本方期待：
```json
{ "zones": [{ "code": "forehead", "label": "额部", "status": "...", "description": "..." }] }
```

**关键差异**：
- `zone`（中文名）→ 我们想要 `code`（英文 key 用于路由、`label`（中文展示名）双字段
- `strength` + `optimization` → 我们目前只用 `description`，可合并

### 2.4 struct（分层）

贵方 doc：`{ layers: [{ layer: "皮肤层", score, status, optimization }] }`
本方期待：`{ layers: [{ code: "skin", label: "皮肤层", status, description }] }`

### 2.5 radar_chart（雷达图）

| 贵方 doc | 本方 |
|---|---|
| `radar_chart: { labels[], keys[], values[], max: 100 }`（ECharts 友好） | `radar: { stype: 82, style: 88, subzone: 85, struct: 80 }`（自绘 SVG，本方不引图表库） |

→ 任一方做转换均可，但**期望贵方按 dict 输出**，减少前端反序列化心智。

### 2.6 aesthetic_optimization

| 贵方 doc | 本方 |
|---|---|
| `{ summary: "总段", directions: ["关键词1", "关键词2"] }` | `optimization: "一段话"` |

→ 本方现状是一段话，可以接受 `summary + directions`，前端展示成"总段 + 关键词标签"，UI 更丰富。**这块愿意按贵方走。**

### 2.7 多出字段（贵方提供，本方暂不使用）

| 字段 | 本方处理 |
|---|---|
| `mapped_project_directions[]` | 暂不展示，本方"项目方向"由本方 4S 业务规则映射 |
| `lead_cta` | 不用，留资文案由本方运营配置 |
| `disclaimer` | 不用，前端 `<DisclaimerFooter>` 硬编码 |
| `safety.hit_words_before/after` | 不用，本方有独立审核链路 |
| `meta.usage / duration_ms` | 收日志可用，不暴露给前端 |
| `provider` 字段 | 收即可 |

→ 这些字段贵方可以照常返回，本方忽略即可，**不构成阻塞**。

---

## 3. 图片访问方式（请贵方明确）

本方走 **OSS 私有桶 + 签名 URL** 方案（合规 R9：禁止公网暴露人脸图、10 天 CRON 删图）：

```
https://venus-prod.oss-cn-hangzhou.aliyuncs.com/photos/abc.jpg
  ?Expires=1719791900
  &OSSAccessKeyId=...
  &Signature=URL-Encoded-Sig
```

特征：
- URL 带 query string，**长度可达 500+ 字符**
- 限时有效（默认 1 小时）
- HTTPS

**❓ 问题 Q1**：贵方 LLM 服务（Qwen-VL / 豆包 Vision）能否直接拉取这种带签名的私有 OSS URL？是否对 URL 长度/特殊字符有限制？

如果不能，备选方案：
- A. 本方临时改为**公开桶** + 短时效（30s）+ 用完立删（合规风险）
- B. 贵方在自己机房接收图片 base64（请求 body 体积 ~3MB，慎选）
- C. 本方推 OSS，贵方读 OSS 内网 endpoint（同 region 的话很快）

---

## 4. 流式 vs 同步（最关键，请贵方明确）

**❓ 问题 Q2**：贵方接口能否按本方 §1 的 SSE 协议提供？

| 选项 | 描述 | 本方工作量 | 贵方工作量 |
|---|---|---|---|
| **A. 贵方改 SSE** | 贵方将 `/analyze-url` 改为 `/v1/analyze` + SSE，按 `LLMEvent` 推事件 | 几乎零，仅对齐子字段命名 | 中：拆 prompt 为 4 段流式，或全文出后切片推送 |
| **B. 本方做适配器** | 贵方保留同步 `/analyze-url`；本方写 `QwenSyncAdapter`，调贵方接口拿全 JSON 后**伪流式**按 4 phase 推 `LLMEvent`（每 phase 间隔 0.5s） | 中：写适配器 + 全部字段映射 | 零 |
| **C. 退化为假进度** | 本方放弃流式 UX，前端轮询 `/api/reports/:id`，Loading 期跑假进度条 | 大：删 SSE 链路、改前端 Loading 页 | 零 |

**本方倾向**：A > B >> C
- A 最干净，且贵方做 4 段流式对你们 prompt 也更可控
- B 退而求其次，UX 是"假"但前端代码 0 改动
- C 体验差，不推荐

---

## 5. 接口路径 & 字段命名规范

**❓ 问题 Q3**：路径用 `/v1/analyze` 还是 `/analyze-url`？请求字段用 camelCase 还是 snake_case？

| 项 | 本方倾向 | 备注 |
|---|---|---|
| 路径 | `/v1/analyze` | 带版本号便于未来兼容 |
| 请求/响应 字段 | camelCase | 与本方 FastAPI / 前端 TS 一致 |
| 时间字段 | ISO 8601 字符串 | `"2026-06-30T12:00:00Z"` |

如果贵方坚持 snake_case，**本方可以在 adapter 里做转换**，仅多一层工作量，不阻塞。

---

## 6. 错误约定

**❓ 问题 Q4**：错误结构是否能统一？

本方建议（SSE 通道内 `type: "error"`）：

```json
{
  "type": "error",
  "error": {
    "code": "IMAGE_QUALITY_LOW" | "IMAGE_URL_UNREACHABLE" | "LLM_TIMEOUT"
          | "LLM_UNAVAILABLE" | "SAFETY_BLOCKED" | "INTERNAL_ERROR",
    "message": "用户可见的中文提示",
    "retryable": true,
    "details": { /* 可选：例如 quality.reasons[] */ }
  }
}
```

如果走同步方案（Q2 选 B/C），错误体可以是 HTTP 4xx/5xx + 同样的 `{code, message, retryable}` 结构。

---

## 7. 联调与上线节奏

**❓ 问题 Q5**：贵方接口什么时候达到可联调状态？是否有沙箱环境？

本方需要：
- 一个**测试环境 base URL**（可以是内网），本方填入 `LLM_QWEN_BASE_URL` 即可联调
- 一组**样例图片** + **样例响应**（成功 + 4 种失败 stage 各一份），用于本方写自动化测试
- 限流策略：QPS / 单图最大耗时 / 失败重试建议

本方时间线（参考）：
- T+0：贵方回复本文 Q1–Q5
- T+3：本方根据回复落地适配 / 改造
- T+5：联调跑通"上传→分析→报告"完整链路
- T+10：上线灰度

---

## 8. 一页纸总结：请贵方回复以下 5 问

| # | 问题 | 选项 |
|---|---|---|
| Q1 | 能否吃 OSS 私有桶**签名 URL**？ | 能 / 不能（说明替代方案） |
| Q2 | 能否提供 **SSE 流式**接口？ | A 贵方改 SSE / B 本方做适配器 / C 退化为假进度 |
| Q3 | 路径与字段命名能否统一为 `/v1/analyze` + camelCase？ | 能 / 不能（保留 snake_case） |
| Q4 | 错误结构能否按 §6 统一？ | 能 / 微调（请提出） |
| Q5 | 联调环境与样例数据何时可提供？ | 日期 + base URL |

---

> **备注**：本文只覆盖**接口协议**层面，不涉及 prompt 工程、模型选型、出图风格等业务问题——那些建议另开会议对齐。
> 如果对差异表/字段映射有任何疑问，可以直接在本文档对应章节下评论 / 起 PR 反馈，本方会在 1 工作日内响应。
