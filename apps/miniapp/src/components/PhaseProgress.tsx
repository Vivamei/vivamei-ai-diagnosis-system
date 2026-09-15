import { View } from '@tarojs/components'

import type { Phase, PhaseStatus } from '@/hooks/useAnalyzeStream'
import './PhaseProgress.css'

const LABELS: Record<Phase, string> = {
  stype: '分相',
  style: '分型',
  subzone: '分区',
  struct: '分层',
}

const ORDER: Phase[] = ['style', 'stype', 'subzone', 'struct']

interface Props {
  states: Record<Phase, { status: PhaseStatus }>
}

export function PhaseProgress({ states }: Props) {
  return (
    <View className='pp'>
      {ORDER.map((p, i) => {
        const s = states[p].status
        const isLast = i === ORDER.length - 1
        const nextActive = !isLast && (states[ORDER[i + 1]].status !== 'idle' || s === 'done')
        return (
          <View className={`pp-seg ${isLast ? 'pp-seg--last' : ''}`} key={p}>
            <View className={`pp-node ${s === 'streaming' ? 'pp-node--streaming' : ''}`}>
              <View className={`pp-dot ${s === 'done' ? 'pp-dot--done' : s === 'streaming' ? 'pp-dot--streaming' : ''}`}>
                {s === 'done' ? '✓' : i + 1}
              </View>
              <View
                className={`pp-label ${s === 'idle' ? '' : 'pp-label--active'} ${s === 'streaming' ? 'pp-label--streaming' : ''}`}
              >
                {LABELS[p]}
              </View>
            </View>
            {!isLast && <View className={`pp-line ${nextActive ? 'pp-line--active' : ''}`} />}
          </View>
        )
      })}
    </View>
  )
}
