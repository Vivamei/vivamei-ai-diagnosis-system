import type { ReactNode } from 'react'
import { Text, View } from '@tarojs/components'

import { BrandLogo } from './BrandLogo'
import { COPY } from '@/config'
import './BrandHeader.css'

export function BrandHeader({ right }: { right?: ReactNode }) {
  return (
    <View className='bh'>
      <View className='bh__left'>
        <BrandLogo size={32} />
        <View>
          <Text className='bh__name'>{COPY.brandName}</Text>
          <Text className='bh__sub'>{COPY.brandSubtitle}</Text>
        </View>
      </View>
      {right}
    </View>
  )
}
