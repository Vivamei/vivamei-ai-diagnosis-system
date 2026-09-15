import { Image } from '@tarojs/components'

import brandLogo from '@/assets/brand-logo.png'

// 品牌 Logo 标记。默认用内置的几何 logo（薇分美学高脚杯几何标记）。
// 配置 TARO_APP_BRAND_LOGO_URL 可覆盖为其他图片；取值须是完整 https URL
// （小程序的 <image> 不走 request 白名单，但不认相对路径），构建时注入，改完需重打包。
const BRAND_LOGO_URL = (process.env.TARO_APP_BRAND_LOGO_URL || '').trim()

export function BrandLogo({ size = 32 }: { size?: number }) {
  return (
    <Image
      className='brand-logo'
      src={BRAND_LOGO_URL || brandLogo}
      // aspectFit 等价于 H5 的 objectFit: contain
      mode='aspectFit'
      style={{ width: `${size}px`, height: `${size}px` }}
    />
  )
}
