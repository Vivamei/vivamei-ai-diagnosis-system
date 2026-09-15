# 第 5 段：LLM 接口契约（v1 初版 schema + 扩展点）

把 LLM 抽象成 **Provider 接口 + 数据契约** 两层：契约是稳定边界，Provider 实现可换（Qwen-VL、DeepSeek、Mock）。

## 5.1 后端 LLM Provider 接口（Python 抽象基类）

```python
# apps/api/app/services/llm/base.py
from typing import AsyncIterator, Literal
from pydantic import BaseModel

class LLMRequest(BaseModel):
    schema_version: Literal["v1"] = "v1"
    task_id: str
    image_url: str                          # OSS 内部签名 URL，10min 有效
    locale: str = "zh-CN"
    # ↓ 扩展点：未来接 8 万版/10 万版传更多上下文
    user_hints: dict | None = None          # e.g. {"age_range":"25-35"}
    prompt_overrides: dict | None = None    # 临时调 prompt（灰度/AB）

class LLMProvider:
    name: str                               # 'qwen-vl' / 'mock' / ...
    async def analyze_stream(
        self, req: LLMRequest
    ) -> AsyncIterator["LLMEvent"]: ...
```

`LLMEvent` 是一条统一的事件流——和 SSE 事件 1:1 对应，但与 HTTP 解耦（便于单测、便于以后改 WebSocket 也不动 provider）：

```python
class LLMEvent(BaseModel):
    type: Literal["phase","delta","phase_done","radar","done","error"]
    phase: Literal["stype","style","subzone","struct"] | None = None
    text: str | None = None                 # delta 用
    payload: dict | None = None             # phase_done 用，结构见 5.2
    radar: dict | None = None               # done 前一帧；归一化 0-100
    error: dict | None = None
```

## 5.2 4S 报告 v1 数据契约（与数据库 4 个 JSON 列对齐）

```jsonc
// stype（分相）— 衰老相型
{
  "primary": "bone",                        // bone | flesh | skin（骨/肉/皮）
  "ratios":  { "bone": 0.55, "flesh": 0.30, "skin": 0.15 },
  "label":   "骨相为主导",
  "narrative": "您面部以骨相支撑为主...",     // 流式文字最终拼接
  "evidence": [                             // 模型给出的判定依据，可选展示
    { "feature": "下颌轮廓", "note": "线条清晰、骨感明显" }
  ]
}

// style（分型）— 气质风格分型；型库由甲方提供
{
  "primary_type": "qing_li",                // 甲方型库 code
  "primary_label": "清丽型",
  "secondary": [
    { "type": "wen_jing", "label": "温静型", "weight": 0.22 }
  ],
  "narrative": "整体偏..."
}

// subzone（分区）— 各部位状况；分区数量由甲方标准定
{
  "zones": [
    {
      "code": "forehead",
      "label": "额部",
      "status": "good",                     // good | watch | attention
      "description": "饱满度尚可，无明显..."
    },
    { "code":"brow_eye","label":"眉眼区","status":"watch","description":"..." }
    // 中面 / 鼻 / 唇 / 下颌轮廓...
  ]
}

// struct（分层）— 4 层
{
  "layers": [
    { "code":"skin",    "label":"皮肤层",   "status":"watch",     "description":"..." },
    { "code":"subcutis","label":"皮下组织", "status":"good",      "description":"..." },
    { "code":"fascia",  "label":"筋膜层",   "status":"attention", "description":"..." },
    { "code":"bone",    "label":"骨骼结构", "status":"good",      "description":"..." }
  ]
}

// 雷达图（done 前一帧推）
{ "stype": 78, "style": 82, "subzone": 74, "struct": 69 }   // 0-100 归一化
```

## 5.3 显式扩展点（不动现有调用方就能加新能力）

| 扩展场景 | 怎么加 | 兼容性 |
|---|---|---|
| **8 万版加 AI 推荐项目** | LLMEvent 增 `type="recommendation"`，payload 含 TOP3 项目 | 老前端会忽略未知事件 |
| **加 AI 风险预警** | `type="warning"`，payload 含规避项目 | 同上 |
| **报告升级 v2**：分区/分层多字段 | `schema_version="v2"`，前端按版本号 switch 渲染 | DB 已有 schema_version 列，老报告仍以 v1 渲染 |
| **换 LLM 厂商** | 新增 `services/llm/deepseek.py` 实现 `LLMProvider` | 只改配置 `LLM_PROVIDER=deepseek` |
| **传 user_hints** | 已预留 `user_hints` 字段；为 null 时同事服务按默认 prompt 走 | 字段可选 |
| **A/B 不同 prompt** | `prompt_overrides` 字段；后端按用户分桶下发 | 字段可选 |
| **LLM 多轮交互**（10 万版客服） | 接口契约扩到 `chat_stream`，与 `analyze_stream` 并列 | 新接口、不影响老接口 |

## 5.4 同事 LLM 服务对外协议（HTTP/SSE，简化版）

LLM 同事的服务对我们而言只暴露一个端点，后端 Provider 简单转译：

```
POST /v1/analyze
Content-Type: application/json
Accept: text/event-stream

Request body:
{
  "schemaVersion": "v1",
  "taskId": "01HW9...",
  "imageUrl": "https://...signed-url...",
  "locale": "zh-CN",
  "userHints": null,
  "promptOverrides": null
}

Response: text/event-stream（事件结构与 5.1 LLMEvent 同形）
```

## 5.5 Mock Provider（本地联调必须）

`services/llm/mock.py` 实现一个内置 Provider：读 `mock/sample_report.json`，按 1s 一帧的节奏吐 delta，模拟真实流式体验。`LLM_PROVIDER=mock` 启动即可在没有同事服务时跑通前端到数据库的全链路。
