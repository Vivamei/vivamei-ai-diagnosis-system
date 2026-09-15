/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 「记住登录」最长天数，缺省 30（见 api/client.ts）。构建时注入。
  readonly VITE_AUTH_MAX_AGE_DAYS?: string;
  // 品牌 Logo 图片地址，配置后替换默认「薇」方块（见 components/BrandLogo.tsx）。
  readonly VITE_BRAND_LOGO_URL?: string;
  // 首页 hero「薇分美学AI⁺」主视觉透明图，缺省用内置 /brand-hero-ai.png（见 config/copy.ts）。
  readonly VITE_BRAND_HERO_ART_URL?: string;
  // 可配置文案，均有默认值（见 config/copy.ts）。
  readonly VITE_BRAND_NAME?: string;
  readonly VITE_BRAND_SUBTITLE?: string;
  readonly VITE_DISCLAIMER_LINE1?: string;
  readonly VITE_DISCLAIMER_LINE2?: string;
  readonly VITE_CTA_REPORT?: string;
  readonly VITE_HOME_TAGLINE?: string;
  readonly VITE_HOME_HERO_LINE1?: string;
  readonly VITE_HOME_HERO_LINE2?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
