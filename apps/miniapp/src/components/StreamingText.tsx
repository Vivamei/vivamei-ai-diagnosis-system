import { Text, View } from '@tarojs/components'

import './StreamingText.css'

interface Props {
  text: string
  active: boolean
}

export function StreamingText({ text, active }: Props) {
  return (
    <View className='st'>
      {text}
      {/* 流式生成中的方块光标，blink 关键帧在 app.css */}
      {active && <Text className='st__cursor'>▌</Text>}
    </View>
  )
}
