// 全站可配置文案。每项对应一个构建期 VITE_* 环境变量，未配置则用下面的默认值。
// 改动方式：在 apps/web/.env(.production) 里设对应变量，重打 web 镜像生效。
// 说明：品牌名 / 英文副标出现在多处（首页、登录、品牌栏、法务页、报告页），统一从这里取，改一处全站生效。
const env = (v: string | undefined, fallback: string) =>
  (v ?? "").trim() || fallback;

export const COPY = {
  // 品牌名 + 英文副标
  brandName: env(import.meta.env.VITE_BRAND_NAME, "薇分美学"),
  brandSubtitle: env(import.meta.env.VITE_BRAND_SUBTITLE, "DIFFERENTIAL AESTHETIC"),

  // 免责声明两行（首页 / 登录页底部）
  disclaimerLine1: env(
    import.meta.env.VITE_DISCLAIMER_LINE1,
    "本报告为美学形象参考，不构成医疗诊断、治疗或术式建议",
  ),
  disclaimerLine2: env(
    import.meta.env.VITE_DISCLAIMER_LINE2,
    "现阶段本测试仅适用于女性",
  ),

  // 报告页底部免责声明两行（锁定为配置，忽略 LLM 返回的 disclaimer）
  reportDisclaimerLine1: env(
    import.meta.env.VITE_REPORT_DISCLAIMER_LINE1,
    "本报告为美学形象参考，不构成医疗诊断、治疗或术式建议。",
  ),
  reportDisclaimerLine2: env(
    import.meta.env.VITE_REPORT_DISCLAIMER_LINE2,
    "个体美学判断存在主观波动，多次结果可能略有差异。",
  ),

  // 报告页 CTA 按钮
  ctaReport: env(
    import.meta.env.VITE_CTA_REPORT,
    "领取你的专属薇分美学4S报告",
  ),

  // 报告页 CTA 上方留资引导语（锁定为配置，忽略 LLM 返回的 lead_cta.text）
  leadText: env(
    import.meta.env.VITE_LEAD_TEXT,
    "填写信息后，专业顾问将结合你的4S报告，为你提供一对一美学建议。",
  ),

  // 达到每日生成上限时的提示（首页「开始测一测」前置拦截）。次数上限由后端 RL_ANALYZE_PER_DAY 配置。
  quotaExhausted: env(
    import.meta.env.VITE_QUOTA_EXHAUSTED,
    "今日测评体验次数已达上限，明天再来体验吧～",
  ),

  // 首页引导文案
  homeTagline: env(
    import.meta.env.VITE_HOME_TAGLINE,
    "拍一张正脸照，AI 出具薇分美学4S诊断参考报告",
  ),  homeHeroLine1: env(import.meta.env.VITE_HOME_HERO_LINE1, "AI 薇分美学4S体系"),
  homeHeroLine2: env(
    import.meta.env.VITE_HOME_HERO_LINE2,
    "分型 · 分相 · 分区 · 分层",
  ),

  // 首页 hero「薇分美学AI⁺」主视觉图案：透明图路径（打进 public/ 的相对路径或完整 URL）。
  // 默认用内置的 /brand-hero-ai.webp；换成设计出的透明图只需覆盖此变量。
  heroArtUrl: env(import.meta.env.VITE_BRAND_HERO_ART_URL, "/brand-hero-ai.webp"),
} as const;
