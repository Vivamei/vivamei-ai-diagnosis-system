import { View } from '@tarojs/components'

import { COPY } from '@/config'
import './DisclaimerFooter.css'

export function DisclaimerFooter() {
  return (
    <View className='df'>
      <View>{COPY.reportDisclaimerLine1}</View>
      <View>{COPY.reportDisclaimerLine2}</View>
    </View>
  )
}
