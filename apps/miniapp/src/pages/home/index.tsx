import { useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'

import { getAnalyzeQuota, getReport, LastTaskStore } from '@/api/analyze'
import { ApiError, AuthStore } from '@/api/client'
import { COPY } from '@/config'
import { requireLogin } from '@/utils/nav'
import './index.css'

const FOUR_S = [
  { k: '分相', e: 'Stype', d: '骨/肉/皮相主导' },
  { k: '分型', e: 'Style', d: '气质风格分型' },
  { k: '分区', e: 'Subzone', d: '美学分区评估' },
  { k: '分层', e: 'Struct', d: '结构层次评估' },
]

export default function Home() {
  const [checking, setChecking] = useState(false)
  const [blockMsg, setBlockMsg] = useState<string | null>(null)
  const [resume, setResume] = useState<{ taskId: string; ready: boolean } | null>(null)

  // 每次回到首页都重查一次：从报告页返回时状态可能已经变了。
  // 425 = 还在生成，404 = 已过期被清，直接抹掉本地记忆；其它错误忽略，不显示入口。
  useDidShow(() => {
    // 首页供游客直接浏览。只有已有登录态时才查询个人报告，不在首屏触发授权登录。
    if (!AuthStore.tokens) {
      setResume(null)
      return
    }
    const last = LastTaskStore.get()
    if (!last) {
      setResume(null)
      return
    }
    getReport(last.taskId)
      .then(() => setResume({ taskId: last.taskId, ready: true }))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 425) {
          setResume({ taskId: last.taskId, ready: false })
        } else if (e instanceof ApiError && e.status === 404) {
          LastTaskStore.clear()
          setResume(null)
        }
      })
  })

  const goResume = () => {
    if (!resume) return
    const page = resume.ready ? 'report' : 'analyzing'
    Taro.navigateTo({ url: `/pages/${page}/index?taskId=${resume.taskId}` })
  }

  // 先查今日配额，超限就原地提示、不进拍照页；查询失败则放行（生成接口仍会兜底限流）。
  const handleStart = async () => {
    if (checking) return
    // 用户主动开始测评后，才进入需要身份信息的登录流程。
    if (!requireLogin()) return
    setChecking(true)
    setBlockMsg(null)
    try {
      const q = await getAnalyzeQuota()
      if (q.blocked) {
        setBlockMsg(COPY.quotaExhausted)
        return
      }
      Taro.navigateTo({ url: '/pages/capture/index' })
    } catch {
      Taro.navigateTo({ url: '/pages/capture/index' })
    } finally {
      setChecking(false)
    }
  }

  return (
    <View>
      <View className='home-hero'>
        <View className='home-hero__name'>{COPY.brandName}</View>
        <View className='home-hero__sub'>{COPY.brandSubtitle}</View>
        <View className='home-hero__lines'>
          <View>{COPY.homeHeroLine1}</View>
          <View>{COPY.homeHeroLine2}</View>
        </View>
      </View>

      <View className='home-body'>
        <View className='home-tagline'>{COPY.homeTagline}</View>

        <View className='home-grid'>
          {FOUR_S.map((c) => (
            <View className='home-cell' key={c.k}>
              <View className='home-cell__inner'>
                <View className='home-cell__k'>
                  {c.k}
                  <Text className='home-cell__e'>{c.e}</Text>
                </View>
                <View className='home-cell__d'>{c.d}</View>
              </View>
            </View>
          ))}
        </View>

        {resume && (
          <View className='home-resume' onClick={goResume}>
            <View>
              <View className='home-resume__title'>
                {resume.ready ? '你有一份薇分美学4S报告已生成' : '你有一份报告正在生成中'}
              </View>
              <View className='home-resume__sub'>
                {resume.ready ? '点此查看报告' : '点此继续查看进度'}
              </View>
            </View>
            <Text className='home-resume__arrow'>›</Text>
          </View>
        )}

        <Button className='home-start' disabled={checking} onClick={handleStart}>
          {checking ? '检测中…' : '开始测一测'}
        </Button>

        {blockMsg && <View className='home-block'>{blockMsg}</View>}

        <View className='home-foot'>
          <View>{COPY.disclaimerLine1}</View>
          <View>{COPY.disclaimerLine2}</View>
        </View>
      </View>
    </View>
  )
}
