# 薇分美学 4S · AI 美学诊断报告 H5 — 技术设计稿

> **项目代号**：venus-4s
> **设计版本**：v1.0
> **出具日期**：2026-06-29
> **依据文档**：`客户修改方案/5万版-报价清单-对外-6.25(3).docx`、`对比结果/4S诊断版-合规风险告知清单.md`
> **本期目标**：可上线的生产 MVP（H5 + 后端服务）

---

## 文档结构

本设计稿分 8 段，每段独立文件放在 `sections/` 下，本文件是合并视图。

| # | 段名 | 文件 |
|---|---|---|
| 1 | 整体架构 | [sections/01-architecture.md](sections/01-architecture.md) |
| 2 | Monorepo 目录结构 | [sections/02-repo-structure.md](sections/02-repo-structure.md) |
| 3 | 数据库 Schema | [sections/03-database-schema.md](sections/03-database-schema.md) |
| 4 | HTTP API 设计 | [sections/04-http-api.md](sections/04-http-api.md) |
| 5 | LLM 接口契约 | [sections/05-llm-contract.md](sections/05-llm-contract.md) |
| 6 | 前端组件与交互 | [sections/06-frontend.md](sections/06-frontend.md) |
| 7 | 合规与隐私 | [sections/07-compliance.md](sections/07-compliance.md) |
| 8 | 测试 / CI / 部署 / 监控 | [sections/08-test-deploy.md](sections/08-test-deploy.md) |

---

## 技术选型总览（一表速读）

| 维度 | 选型 | 决策依据 |
|---|---|---|
| 前端 | React 18 + Vite + TypeScript + React Router 7 | 用户指定；SVG 自绘雷达图，不引图表库 |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + Alembic | 用户指定；AI/SSE/多模态生态最好 |
| 数据库 | MySQL 8.0 + Redis 7 | 用户指定；运维熟悉度高 |
| 对象存储 | 阿里云 OSS（STS 直传） | 用户指定；与内容安全同生态 |
| 内容安全 | 阿里云内容安全（文本 + 图片，含医疗专项词库） | 同上；医美违禁词库最全 |
| 短信 | 阿里云短信 | 同生态；模板审核流程清楚 |
| LLM | 通义 Qwen-VL（同事提供独立 HTTP/SSE 服务） | 用户指定；后端封装 Provider 抽象层 |
| 部署 | 阿里云 ECS 4 核 8G + Docker Compose + Nginx | MVP 单机最省；月成本 ¥250 |
| 仓库 | Monorepo（apps/ + packages/ + infra/ + docs/） | 单人/小团队最省心 |
| 鉴权 | 手机号 + 短信验证码 + JWT（access 1h / refresh 7d） | 不依赖微信资质，外部渠道可用 |
| 合规 | 同步做齐 R1-R12 风险处置（含 ConsentDialog / AiBadge / 内容安全双层 / KMS 加密 / 10 天过期） | 4 项红色风险叠加，命门 |
| CI/CD | GitHub Actions → 阿里云 ACR → ssh ECS docker compose up | trunk-based，5 分钟回滚 |
| 监控 | 阿里云云监控 + SLS 日志服务 + 飞书机器人报警 | 预算敏感，不上 Prometheus |

---

## 范围内（In Scope）

- C 端 H5 6 页（首页 / 拍照上传 / 分析中 / 4S 报告 / 雷达图详情 / 留资预约）
- 后端 4 类 API（鉴权 / 上传 / 分析 / 留资）+ SSE 流式
- LLM Provider 抽象层 + Mock Provider（联调用）
- 内容安全双层 + 敏感词库
- 合规处置（R1-R12）+ 隐私协议 v1.0
- 留资 CSV 导出脚本
- 单机 ECS 部署 + 数据备份 + 监控报警
- 文档：API（Swagger）/ 部署 / 运维手册 / 培训

## 范围外（Out of Scope）

- 管理后台（本期不做，仅留资 CSV）
- 邀请助力 / 颜值排行榜 / 海报裂变（v3.0 已移除）
- 项目库 / 项目详情页（5 万版不含）
- 现场大屏 H5（8 万版能力）
- AI 推荐项目 / 风险预警 / 反向识别 / 智能客服（8 万/10 万版能力）
- LLM 算法本身的训练与 Prompt 工程（同事负责）
- 医疗机构许可证 / 医疗广告审查证明 / 网信办 AIGC 备案（甲方义务）
- 多端适配（小程序 / 抖音 / 支付宝）

---

## 与外部团队的协作边界

| 事项 | 我方 | 同事（LLM） | 甲方 |
|---|---|---|---|
| LLM 推理服务 | 调用 + Provider 封装 | **实现 + 部署 + Prompt** | 提供 4S 型库 |
| LLM 接口 schema | **共同评审 + 落 contract** | 共同评审 + 实现 | — |
| 4S 专业标准 | 集成到 Prompt | 与同事配合 | **提供型库/分相/分区/分层标准 + 标注样例** |
| 域名 / ICP / 公众号白名单 | 写入运维手册 | — | **办理** |
| 医疗广告审查证明 | — | — | **办理** |
| 阿里云账号 / KMS / 短信模板 | 协助申请 | — | **主账号 + 实名** |

---

## 待定 / 风险项

1. **同事 LLM 服务 SLA 未定**：超时/失败率、并发上限。需在 Provider 评审时同步约定，并准备降级策略
2. **甲方 4S 标准交付节奏**：合同 6.4 明确为先决条件，但实操可能延期。建议加里程碑监控
3. **iOS Safari 在微信内的 SSE 稳定性**：业界普遍反馈微信 X5/WKWebView 偶发 SSE "半连接"。`useSse` 已设计兜底重连，仍需上线前真机验证
4. **阿里云内容安全的医美专项词库覆盖度**：上线前需用历史违规样本回归一次，必要时补本地词库

---

## 附录

### A. 与 11-三档报价 / 客户修改方案 v3.0 的对齐情况

| 客户修改方案条款 | 本设计落点 |
|---|---|
| 6.1 总报价 5 万（含税） | — |
| 6.3 报价包含·完整源代码 + 数据库脚本 | 第 2/3 段 |
| 6.3 报价包含·4S 美学报告 + 4S 雷达图 | 第 5/6 段 |
| 6.3 报价包含·UI 设计稿（沿用现有 4S 原型） | 第 6 段 |
| 6.3 报价包含·API 接口文档 + 部署文档 | 第 4/8 段 |
| 6.3 报价包含·首年云服务器 + 域名 + SSL | 第 8 段 |
| 6.4 甲方提供专业标准 | 第 5 段（LLM 接口预留 prompt_overrides）+ 协作边界表 |
| 4.1 用户端 8 页面（含 6 主页 + 2 法务） | 第 6 段路由表 |
| 4.2 后端接口 ①②③④ | 第 4 段 |
| 4.3 合规与备案 | 第 7 段 |

### B. 关键决策回顾

所有重大决策均经用户确认（详见澄清问题阶段）：
- 项目定位：可上线生产 MVP（非 demo / 非 POC）
- 后端：Python + FastAPI（非 Node.js / Java）
- 前端：React + Vite（重写原型 HTML 为组件）
- 数据库：MySQL 8 + Redis 7（非 PostgreSQL / SQLite）
- 云：阿里云全家桶（OSS / 内容安全 / 短信 / ECS）
- 身份：手机号 + 短信验证码（非微信 OAuth / 免登录）
- 部署：Docker Compose 单机（非 K8s / Serverless）
- 后台：本期不做（仅留资 CSV 导出）
- 合规：同步做齐
- 仓库：Monorepo
- LLM：通义 Qwen-VL，由另一位同事负责服务实现；我方共同参与接口评审，对外暴露统一 Provider 抽象
