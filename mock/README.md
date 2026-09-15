# mock/ —— 本地 mock 数据

本地开发用的假报告数据，直接读 JSON，不连真实 LLM。

| 文件 | 用途 |
|------|------|
| `sample_report.json` | 一份完整的分析报告样例（分型/分相/分区/分层 + 雷达 + 优化建议） |

## 谁读它

- `apps/api/app/services/llm/mock.py` —— 进程内 `MockLLMProvider`（`LLM_PROVIDER=mock` 时启用），把这份数据逐字段伪流式吐成 SSE，模拟真实分析节奏。
- `apps/api/mock_llm_server.py` —— 独立 mock HTTP/SSE 服务，走真实 HTTP 链路联调 `QwenLLMProvider`。

## 怎么用

在 `config/dev.env` 设 `LLM_PROVIDER=mock` 即走进程内 mock，无需任何外部服务；改这份 JSON 就能改 mock 出的报告内容。
