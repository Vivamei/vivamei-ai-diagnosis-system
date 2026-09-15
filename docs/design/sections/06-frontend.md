# 第 6 段：前端组件与关键交互

视觉色板和组件命名沿用现有原型 HTML（`对比结果/4S诊断版-原型demo.html`），把它当 design token 来源，不重新设计风格。

> §6.1 – §6.7 描述的是 `apps/web`（React + Vite 的 H5 主线）。
> 后续增补的微信小程序端在 `apps/miniapp`（Taro），与 `apps/web` 并存，见 §6.8。

## 6.1 路由

```
/                 → Home              (P1)
/capture          → Capture           (P2)
/analyzing/:id    → Analyzing         (P3，SSE 流式)
/report/:id       → Report            (P4，4S 雷达图 + 四维卡片)
/report/:id/:axis → RadarDetail       (P5，stype|style|subzone|struct)
/booking          → Booking           (P6，留资预约)
/legal/privacy    → 隐私政策（静态 MD 渲染）
/legal/terms      → 用户协议（静态 MD 渲染）
```

React Router 7（最新稳定版），所有路由懒加载（`React.lazy + Suspense`）。

## 6.2 全局态：极简，不引 Redux/Zustand

只有两类共享状态，自己写两个 Context 足够：

- **AuthContext**：accessToken / refreshToken / user / 自动刷新逻辑
- **ConsentContext**：当前隐私协议版本是否已勾选（localStorage 持久）

业务态（task/report）走 URL 参数 + `useSWR` 缓存，不进全局 store。

## 6.3 核心组件清单（10 个，覆盖所有页面）

| 组件 | 用途 | 复杂度 |
|---|---|---|
| `<RadarChart>` | 4S 四轴雷达图，可点击切轴 | 中（SVG 自绘，不引图表库） |
| `<DimensionCard>` | 分相/分型/分区/分层 任一维度卡片 | 低 |
| `<StreamingText>` | 流式打字机效果，配合 SSE delta | 低 |
| `<PhaseProgress>` | 4 步进度条（已完成/进行中/未开始） | 低 |
| `<PhotoCapture>` | 调起相机/相册 + 多角度引导 | 中 |
| `<ConsentDialog>` | 隐私协议强制勾选（合规 R9） | 低 |
| `<AiBadge>` | "AI 生成·仅供参考" 角标（合规 R10） | 低 |
| `<DisclaimerFooter>` | 报告页"不构成医疗诊断/治疗建议"页脚（合规 R2） | 低 |
| `<SmsCodeInput>` | 6 位验证码输入 + 60s 倒计时 | 低 |
| `<ReportExport>` | 报告导出：长图（html2canvas）+ PDF（jspdf 分页）；均含 AIGC 水印 | 中 |

**不引图表库的原因**：雷达图只有 4 个轴，自绘 SVG ~80 行，比拉 ECharts（~400KB）/Recharts（~100KB gzip）都划算，与原型 HTML 的视觉风格也最一致。

## 6.4 关键交互：SSE 流式渲染

`useSse` Hook 封装 EventSource，对接 4.3 的事件流：

```typescript
// apps/web/src/hooks/useSse.ts
type SseState = {
  phases: Record<Phase, { status: 'idle'|'streaming'|'done', text: string, payload?: any }>
  radar?: RadarScores
  done: boolean
  error?: { code: string, retryable: boolean }
}

function useAnalyzeStream(taskId: string): SseState {
  // 内部用 EventSource，监听 phase/delta/phase_done/radar/done/error
  // 维护按维度聚合的 phases 状态
  // 断线自动重连（浏览器内置 + Last-Event-ID）
  // 组件卸载时 close
}
```

**Analyzing 页（P3）渲染**：
- 顶部 `<PhaseProgress>` 显示 4 步进度
- 中部按维度展开 4 个 `<StreamingText>`，当前 phase 跑打字机，其他静默
- 拿到 `done` 事件后 `navigate('/report/' + taskId)`
- 拿到 `error` 且 `retryable=true` 时显示重试按钮，否则降级提示

**Report 页（P4）渲染**：
- 顶部 `<RadarChart>`，4 个轴可点
- 下方 4 个 `<DimensionCard>` 折叠展开
- 底部固定 `<DisclaimerFooter>` + `<AiBadge>`
- "查看完整维度"跳 `/report/:id/:axis`（P5）
- "保存为长图" / "保存为 PDF" 调 `<ReportExport>`（PNG 长图与 A4 分页 PDF，均含 AIGC 水印 + 免责）
- "预约到店面诊"跳 `/booking`

## 6.5 关键交互：拍照与上传

```
用户进 P2
 └→ <ConsentDialog> 强制勾选（未勾选 → 拍照按钮 disabled）
    └→ 点"开始拍照"
       └→ <PhotoCapture>：input[type=file][accept=image/*][capture=user]
          └→ 拿到 File 后前端压缩（Pica，长边 ≤ 1920px，目标 < 1MB）
             └→ POST /api/upload/token 拿 STS 凭证
                └→ 直传 OSS（带进度条）
                   └→ POST /api/photos 登记
                      └→ POST /api/analyze 创建任务 → 拿 taskId
                         └→ navigate(`/analyzing/${taskId}`)
```

**为什么前端压缩**：原图 4-8MB，压到 800KB 上传更快、OSS 流量更省、内容安全机审更快；同时 1920 长边对多模态识别精度足够。

## 6.6 兼容性与移动端细节

- **目标**：iOS Safari 14+ / Android Chrome 80+ / 微信内置浏览器（X5/WKWebView）
- **设计稿基准 375×667**，用 viewport meta + rem 字号缩放，最大宽度 420px 居中
- **拍照**：iOS 必须 `<input>` 触发用户手势（不能用 JS 主动调起 getUserMedia 否则被拦截）
- **SSE**：iOS WKWebView 对 EventSource 支持完善；微信内偶发"半连接"问题——`useSse` 加 30s 没收到 ping 自动重连兜底
- **键盘**：iOS 输入手机号时 viewport 不缩放（`<input type="tel" inputmode="numeric">`）

## 6.7 性能预算

| 指标 | 预算 |
|---|---|
| 首屏 LCP | ≤ 2s（4G 下，Nginx gzip + 静态资源 CDN/缓存） |
| 主 bundle gzipped | ≤ 80KB（React 18 + Router 7 + 自有代码） |
| 路由代码分割 | 每页 ≤ 20KB gzip |
| 拍照页 → SSE 第一帧 | ≤ 8s（含上传 + 内容安全 + LLM 首 token） |

## 6.8 微信小程序端（apps/miniapp，Taro）

在 `apps/web` 之外新增一套 Taro 4.2 代码，**一份源码编译出两个产物**：微信原生小程序（`weapp`）
与 H5（`h5`）。`apps/web` 保持不动，仍是既有 H5 主线；`apps/miniapp` 的 H5 产物主要用于
在浏览器里调页面，不必开小程序开发者工具。

后端只有一套 `apps/api`，三个前端产物共用同一批接口。

### 与 apps/web 的技术选型差异

| | `apps/web` | `apps/miniapp` |
|---|---|---|
| 框架 | React 18 + Vite + React Router 7 | Taro 4.2 + React 18 + webpack5 |
| 路由 | React Router，URL 路径 | `src/app.config.ts` 的 `pages` 数组（小程序页面栈） |
| 流式 | SSE（`EventSource`） | 同一 SSE（`Taro.request + enableChunked`） |
| 雷达图 | 自绘 SVG | 小程序无内联 SVG，改用 `<Canvas>` + `createCanvasContext` |
| 登录 | 仅短信验证码 | 微信一键登录 + 短信验证码**双模** |

**小程序如何读取 SSE**：微信没有原生 `EventSource`，但
`Taro.request({ enableChunked: true })` 可通过 `onChunkReceived` 增量读取响应。
客户端自行完成 UTF-8 与 SSE 帧解析，直接复用
`GET /api/analyze/{task_id}/stream`；事件契约
（`queued`/`phase`/`delta`/`phase_done`/`radar`/`done`/`error`）与 H5 一致。

### 双端差异的收敛点

只有三处，其余代码共用。统一用构建期常量 `process.env.TARO_ENV` 分支，
未命中的分支会被 webpack 摇掉，产物里不残留另一端的代码。

1. **请求基址**：小程序发不了相对路径请求，必须绝对域名；H5 默认留空走同源
   （开发期 devServer 代理、生产期 Nginx 反代 `/api`），因此**默认部署无需后端 CORS**。
2. **登录形态**：H5 没有 `wx.login` 与 `open-type="getPhoneNumber"`，只渲染短信登录；
   小程序默认微信一键登录，并提供切到短信的入口，微信侧不可用时自动降级。
3. **域名白名单**：小程序要在微信后台分别配置 request 与 uploadFile；SSE 走 request，不需要 socket。

### 页面清单（本轮范围）

```
pages/home/index        首页
pages/login/index       登录（微信一键 + 短信双模）
pages/capture/index     拍照上传
pages/analyzing/index   分析中（分块 SSE）
pages/report/index      报告（4S 雷达图）
```

RadarDetail（P5）、Booking（P6）与 legal 静态页暂未迁移到小程序端。

具体的构建命令、配置项、Nginx SSE 反代要求与排查清单，见
[references/MINIAPP.md](../../references/MINIAPP.md)。
