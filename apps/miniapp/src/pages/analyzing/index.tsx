import { useEffect, useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'

import { getPublicConfig } from '@/api/meta'
import { AiGeneratedNotice } from '@/components/AiGeneratedNotice'
import { BrandHeader } from '@/components/BrandHeader'
import { PhaseProgress } from '@/components/PhaseProgress'
import { StreamingText } from '@/components/StreamingText'
import { Phase, useAnalyzeStream } from '@/hooks/useAnalyzeStream'
import { requireLogin } from '@/utils/nav'
import './index.css'

const LABELS: Record<Phase, string> = {
  style: '分型 Style',
  stype: '分相 Stype',
  subzone: '分区 Subzone',
  struct: '分层 Struct',
}

// 分析页文案/时长的兜底默认值。真实值由后端 /api/config 提供（可在外置 .env 调整）。
const FALLBACK_CFG = {
  analyzeEtaSeconds: 150,
  analyzeTitlePreparing: 'AI 分析准备中…',
  analyzeTitleAnalyzing: 'AI 正在为您分析…',
  analyzeSubtitle: '分型 · 分相 · 分区 · 分层',
  analyzeWaitHints: [
    '正在读取面部轮廓与光影结构…',
    '比对分型 / 分相 / 分区 / 分层四维模型…',
    '结合个人特征生成美学建议…',
    '即将完成，正在整理报告…',
  ],
  analyzeWaitNote: '请勿关闭页面',
}

// 把预计秒数格式化成友好文案：>=90s 用「分钟」，否则用「秒」。
function fmtEta(sec: number): string {
  if (sec >= 90) {
    const lo = Math.floor(sec / 60)
    const hi = Math.ceil(sec / 60)
    return `预计 ${lo === hi ? lo : `${lo}–${hi}`} 分钟`
  }
  return `预计 ${sec} 秒`
}

export default function Analyzing() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [cfg, setCfg] = useState(FALLBACK_CFG)
  const [elapsed, setElapsed] = useState(0)
  const stream = useAnalyzeStream(taskId)

  useLoad((opts: Record<string, string>) => {
    if (!requireLogin()) return
    if (opts.taskId) setTaskId(opts.taskId)
    getPublicConfig()
      .then((d) =>
        setCfg({
          analyzeEtaSeconds: d.analyzeEtaSeconds ?? FALLBACK_CFG.analyzeEtaSeconds,
          analyzeTitlePreparing: d.analyzeTitlePreparing || FALLBACK_CFG.analyzeTitlePreparing,
          analyzeTitleAnalyzing: d.analyzeTitleAnalyzing || FALLBACK_CFG.analyzeTitleAnalyzing,
          analyzeSubtitle: d.analyzeSubtitle || FALLBACK_CFG.analyzeSubtitle,
          analyzeWaitHints:
            Array.isArray(d.analyzeWaitHints) && d.analyzeWaitHints.length
              ? d.analyzeWaitHints
              : FALLBACK_CFG.analyzeWaitHints,
          analyzeWaitNote: d.analyzeWaitNote || FALLBACK_CFG.analyzeWaitNote,
        }),
      )
      .catch(() => {
        // 配置拉取失败忽略，用兜底默认值
      })
  })

  useEffect(() => {
    if (stream.done && taskId) {
      Taro.redirectTo({ url: `/pages/report/index?taskId=${taskId}` })
    }
  }, [stream.done, taskId])

  const anyActive = (Object.keys(LABELS) as Phase[]).some(
    (p) => stream.phases[p].status !== 'idle',
  )
  const waiting = !anyActive && !stream.done && !stream.error

  // 等待期计时：首个 phase 事件到达前每秒 +1，进入分析/出错后停止
  useEffect(() => {
    if (!waiting) return
    const t = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [waiting])

  // 渐进提示 + 渐近进度（永远到不了 100，真数据到达才收尾）。
  // 时间常数取 eta/2.3，使 elapsed≈eta 时逼近约 90%。
  const eta = cfg.analyzeEtaSeconds
  const hints = cfg.analyzeWaitHints
  const hintStep = Math.max(1, eta / hints.length)
  const hint = hints[Math.min(Math.floor(elapsed / hintStep), hints.length - 1)]
  const tau = Math.max(1, eta / 2.3)
  const pct = Math.min(96, Math.round((1 - Math.exp(-elapsed / tau)) * 100))

  // 排队态：后端还没给这个任务分到并发槽，展示位次而非渐进进度条。
  const queued = waiting && stream.queueAhead != null
  const queueAhead = stream.queueAhead ?? 0

  if (stream.error) {
    return (
      <View className='an-page'>
        <BrandHeader />
        <View className='an-err'>
          <View className='an-err__title'>分析失败</View>
          <View className='an-err__msg'>
            {stream.error.message || '分析过程中出现问题，请稍后重试。'}
          </View>
          <View className='an-err__code'>错误码：{stream.error.code}</View>
          <View className='an-err__actions'>
            {stream.error.retryable && (
              <Button
                className='an-err__btn'
                onClick={() =>
                  Taro.redirectTo({ url: `/pages/analyzing/index?taskId=${taskId}` })
                }
              >
                重试
              </Button>
            )}
            <Button
              className='an-err__btn an-err__btn--ghost'
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}
            >
              返回首页
            </Button>
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className='an-page'>
      <BrandHeader />
      <AiGeneratedNotice />

      <View className='an-head'>
        <View className='an-spinner' />
        <Text className='an-title'>
          {anyActive ? cfg.analyzeTitleAnalyzing : cfg.analyzeTitlePreparing}
        </Text>
      </View>
      <View className='an-sub'>{cfg.analyzeSubtitle}</View>

      {waiting && (
        <View className='an-wait'>
          <View className='an-wait__row'>
            <Text className='an-wait__hint'>
              {queued
                ? queueAhead > 0
                  ? `排队中，前面还有 ${queueAhead} 人`
                  : '即将开始，正在为您准备…'
                : hint}
            </Text>
            <Text className='an-wait__pct'>
              {queued ? (queueAhead > 0 ? `第 ${queueAhead + 1} 位` : '即将开始') : `${pct}%`}
            </Text>
          </View>
          {!queued && (
            <View className='an-bar'>
              <View className='an-bar__fill' style={{ width: `${pct}%` }} />
            </View>
          )}
          <View className='an-wait__foot'>
            <Text>已等待 {elapsed}s</Text>
            <Text>
              {queued
                ? `活动高峰期，正在排队处理，${cfg.analyzeWaitNote}`
                : `${fmtEta(eta)}，${cfg.analyzeWaitNote}`}
            </Text>
          </View>
        </View>
      )}

      <PhaseProgress states={stream.phases} />

      <View className='an-list'>
        {(Object.keys(LABELS) as Phase[]).map((p) => {
          const st = stream.phases[p]
          const isIdle = st.status === 'idle'
          const isStreaming = st.status === 'streaming'
          return (
            <View
              className={`an-card ${isIdle ? 'an-card--idle' : ''} ${
                isStreaming ? 'an-card--streaming' : ''
              }`}
              key={p}
            >
              <View className='an-card__row'>
                <Text className='an-card__name'>{LABELS[p]}</Text>
                <Text className={`an-card__state an-card__state--${st.status}`}>
                  {st.status === 'done' ? '✓ 完成' : isStreaming ? '生成中…' : '等待中'}
                </Text>
              </View>
              {isIdle ? (
                <View className='an-skels'>
                  <View className='skeleton-line' style={{ width: '92%' }} />
                  <View className='skeleton-line' style={{ width: '78%' }} />
                  <View className='skeleton-line' style={{ width: '64%' }} />
                </View>
              ) : (
                <StreamingText text={st.text} active={isStreaming} />
              )}
            </View>
          )
        })}
      </View>
    </View>
  )
}
