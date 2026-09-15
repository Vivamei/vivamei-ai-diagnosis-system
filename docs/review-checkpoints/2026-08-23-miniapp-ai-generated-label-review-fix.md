# 小程序 AI 生成内容标识提审整改检查点（2026-08-23）

## Fixed point / base

- Git base SHA：不适用。当前交付目录不是 Git worktree。
- 增量起点：`docs/review-checkpoints/2026-08-23-miniapp-login-review-fix.md` 之后的本次 AI 标识整改。
- 整改前替代基线（SHA-256）：
  - `apps/miniapp/src/pages/analyzing/index.tsx`：`EA03E0744807AC5D344270FF8561E1FA0B65BFAE36FD71CCE816109FEB811987`
  - `apps/miniapp/src/pages/report/index.tsx`：`EDC4A9795F7257F91E25D3F1BF02DCD70489625ACA3C442770748CD084FA8AE9`
  - `apps/miniapp/src/pages/radar-detail/index.tsx`：`3064463F7ED0A5FD6FD0973CF0AEF4BB318349A26232089E4BFD963C833F53A2`
  - `apps/miniapp/src/components/ReportExport.tsx`：`82122EB04C32266AF6C864E08B9141682AD4F3F58DBA71A1342075766BFFABF1`
  - `apps/miniapp/scripts/check-review-compliance.mjs`：`21830D4F28F3CABF1A94B53EAC0AB6B108D147B9C0F2B05E1F293FFABC5D635C`
  - `AiGeneratedNotice.tsx/.css`：整改前不存在。
- 本检查点后的核心源码指纹（SHA-256）：
  - `apps/miniapp/src/components/AiGeneratedNotice.tsx`：`786C33DF2A5EC15A9B08C4A4489800E9EA7E43312037A3378053403EF2D19467`
  - `apps/miniapp/src/components/AiGeneratedNotice.css`：`DA19B7D137FB1D9AB9C935C7AD506967076C70F0FCA572914B9D1E4F68E188FB`
  - `apps/miniapp/src/pages/analyzing/index.tsx`：`982119BC876E072FC4798331320DE2BBE6058F08C8BCC5370315182C8C6299A8`
  - `apps/miniapp/src/pages/report/index.tsx`：`816CFFE97388542FBA86F209F80251EDC3D824550A36DACE89225A59BB6A8F6B`
  - `apps/miniapp/src/pages/radar-detail/index.tsx`：`5524D63A22B5F8DAD82633F91E1AC0B83965F93AB250CB2D4DC80C46DD8712E5`
  - `apps/miniapp/src/components/ReportExport.tsx`：`672925033B9C209DF61E62669106D3E55D02C352D6A0B8694500AA428F0713A6`
  - `apps/miniapp/scripts/check-review-compliance.mjs`：`3CEC227D480EC74D92FF67DDC3FA6E96791D0E0B712D187DAFA70D12F2952FEB`

## 审查范围

- AI 实时分析页、完整报告页、雷达维度详情页。
- 保存到相册的 AI 报告长图。
- AI 生成内容标识的提审自动检查和生产微信小程序构建产物。
- 不含微信公众平台服务类目配置；该配置不在代码仓库内。

## 发现与修复

1. 原报告页仅在页头显示 10px 的“AI 生成 · 仅供参考”小标签，分析页和详情页没有统一显著标识。
   - 新增全宽、高对比、加粗的 `AiGeneratedNotice`，采用官方正面示例原文“本服务为AI生成内容，结果仅供参考”。
2. AI 实时生成内容与报告详情缺少持续可见的来源说明。
   - 在分析页、完整报告页、雷达详情页首屏页头下方均展示统一标识。
3. 导出长图仅有较弱的右下角水印。
   - 在长图顶部加入同一显著说明，并保留“AI生成 · 仅供参考”水印。
4. 自动提审检查未覆盖 AI 标识。
   - 新增 5 项检查，覆盖标识文案、三个页面及导出图片，总检查数从 8 项增至 13 项。

## 验证结果

- `pnpm --dir apps/miniapp run check:review-compliance`：通过（13 项）。
- `pnpm --dir apps/miniapp exec tsc --noEmit --skipLibCheck`：通过。
- `pnpm --dir apps/miniapp run build:weapp`：完成，生产产物于 2026-08-23 20:03 重新生成。
- `pnpm --dir apps/miniapp run check:weapp-wxss`：通过（10 个 WXSS 文件）。
- 构建产物核验：
  - `apps/miniapp/dist/weapp/common.js` 包含“本服务为AI生成内容，结果仅供参考”，SHA-256 为 `3A30878E733CB19452EEA49317B223D3BB4FFEBEE603B0C6D56355502B43E019`。
  - `apps/miniapp/dist/weapp/common.wxss` 包含 `.ai-generated-notice`、2px 等效描边、14px 等效加粗正文和高对比背景样式。

## 剩余阻塞与风险

- 代码无法修改微信公众平台的服务类目。提交审核前，账号管理员仍须添加“深度合成 → AI问答”类目并确保类目审核/资质状态有效；只上传新代码而不补类目，仍会被拒。
- 当前环境未执行微信开发者工具预览或真机检查。上传前需确认分析页、报告页和雷达详情页首屏均能看到完整标识，且没有被胶囊按钮或安全区遮挡。
- 本次不需要修改后端接口；未变更 API、数据库或服务端部署。
