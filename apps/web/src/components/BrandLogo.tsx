// 品牌 Logo 标记。默认用内置的几何 logo /brand-logo.png（薇分美学高脚杯几何标记）。
// 配置 VITE_BRAND_LOGO_URL 可覆盖为其他图片；取值为打进 public/ 的相对路径或完整 URL，构建时注入，改完需重打 web。
const BRAND_LOGO_URL =
  (import.meta.env.VITE_BRAND_LOGO_URL ?? "").trim() || "/brand-logo.png";

export function BrandLogo({ size = 32 }: { size?: number }) {
  return (
    <img
      src={BRAND_LOGO_URL}
      alt="薇分美学"
      width={size}
      height={size}
      style={{ objectFit: "contain", display: "block" }}
    />
  );
}
