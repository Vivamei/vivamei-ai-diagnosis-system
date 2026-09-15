// 本文件读的 TARO_APP_* 来自 apps/miniapp/.env.*，而那两个文件由 config/frontend.env
// （前端配置唯一真源，H5 与小程序共用）经 scripts/gen-frontend-env.mjs 生成，别去手改。
//
// 小程序发不了相对路径请求，必须配完整域名，且该域名要在微信后台「request 合法域名」
// 里加白名单。分析进度也通过该域名的分块 SSE 请求读取，不再需要 socket 合法域名。
// H5 相反：默认留空走同源相对路径，开发期由
// devServer.proxy 转发、生产由 Nginx 反代 /api，天然无跨域，不必开后端 CORS。
// 两端都可用 TARO_APP_API_BASE 覆盖（Taro 只注入 TARO_APP_ 前缀的环境变量）；H5 只有在
// 前端挂独立域名时才需要填，那时后端必须同步配 CORS_ORIGINS。
const DEFAULT_BASE = process.env.TARO_ENV === 'h5' ? '' : 'http://localhost:8080'
const API_BASE = (process.env.TARO_APP_API_BASE || DEFAULT_BASE).replace(/\/+$/, '')

export const config = {
  apiBase: API_BASE,
  // 「记住登录」最长天数，对齐后端 JWT_REFRESH_TTL_SECONDS（默认 604800s = 7 天）。
  authMaxAgeDays: Number(process.env.TARO_APP_AUTH_MAX_AGE_DAYS) || 7,
  // 隐私协议版本，与 H5 的 ConsentContext.CURRENT_VER 保持一致，后端按此值记 consent_ver。
  consentVer: 'v1.0',
}

// 可配置文案，与 H5 的 apps/web/src/config/copy.ts 一一对应，值同源于 config/frontend.env。
// 每项必须写成完整的 process.env.TARO_APP_XXX 字面量：Taro 是编译期做字符串替换，
// 动态取键（env[name]）在小程序里拿不到值。未配则回落到下面的默认值。
const env = (v: string | undefined, fallback: string) => (v ?? '').trim() || fallback

export const COPY = {
  brandName: env(process.env.TARO_APP_BRAND_NAME, '薇分美学'),
  brandSubtitle: env(process.env.TARO_APP_BRAND_SUBTITLE, 'DIFFERENTIAL AESTHETIC'),
  disclaimerLine1: env(
    process.env.TARO_APP_DISCLAIMER_LINE1,
    '本报告为美学形象参考，不构成医疗诊断、治疗或术式建议',
  ),
  disclaimerLine2: env(process.env.TARO_APP_DISCLAIMER_LINE2, '现阶段本测试仅适用于女性'),
  reportDisclaimerLine1: env(
    process.env.TARO_APP_REPORT_DISCLAIMER_LINE1,
    '本报告为美学形象参考，不构成医疗诊断、治疗或术式建议。',
  ),
  reportDisclaimerLine2: env(
    process.env.TARO_APP_REPORT_DISCLAIMER_LINE2,
    '个体美学判断存在主观波动，多次结果可能略有差异。',
  ),
  ctaReport: env(process.env.TARO_APP_CTA_REPORT, '领取你的专属薇分美学4S报告'),
  leadText: env(
    process.env.TARO_APP_LEAD_TEXT,
    '填写信息后，专业顾问将结合你的4S报告，为你提供一对一美学建议。',
  ),
  quotaExhausted: env(
    process.env.TARO_APP_QUOTA_EXHAUSTED,
    '今日测评体验次数已达上限，明天再来体验吧～',
  ),
  homeTagline: env(
    process.env.TARO_APP_HOME_TAGLINE,
    '拍一张正脸照，AI 出具薇分美学4S诊断参考报告',
  ),
  homeHeroLine1: env(process.env.TARO_APP_HOME_HERO_LINE1, 'AI 薇分美学4S体系'),
  homeHeroLine2: env(process.env.TARO_APP_HOME_HERO_LINE2, '分型 · 分相 · 分区 · 分层'),
} as const
