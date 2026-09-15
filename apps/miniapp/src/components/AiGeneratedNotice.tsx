import { Text, View } from '@tarojs/components'

import './AiGeneratedNotice.css'

export const AI_GENERATED_NOTICE = '本服务为AI生成内容，结果仅供参考'

export function AiGeneratedNotice() {
  return (
    <View className='ai-generated-notice'>
      <Text className='ai-generated-notice__tag'>AI生成</Text>
      <Text className='ai-generated-notice__text'>{AI_GENERATED_NOTICE}</Text>
    </View>
  )
}
