import { useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'

import { getReport, ReportResp } from '@/api/analyze'
import { AiGeneratedNotice } from '@/components/AiGeneratedNotice'
import { BrandHeader } from '@/components/BrandHeader'
import { DisclaimerFooter } from '@/components/DisclaimerFooter'
import { ReportExport } from '@/components/ReportExport'
import { requireLogin } from '@/utils/nav'
import './index.css'

const AXIS_META: Record<string, { cn: string; en: string; accent: string }> = {
  stype: { cn: '分相', en: 'Stype', accent: '#c99048' },
  style: { cn: '分型', en: 'Style', accent: '#cc5f4f' },
  subzone: { cn: '分区', en: 'Subzone', accent: '#7a8f5a' },
  struct: { cn: '分层', en: 'Struct', accent: '#5a7896' },
}

// H5 用 `${accent}55` 这类 8 位十六进制带透明度，低版本基础库的 WXSS 不一定认，
// 这里统一换算成 rgba()，颜色值与 H5 一致（0x55≈0.33 / 0xaa≈0.67 / 0x22≈0.13）。
const rgba = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

interface ZoneItem {
  code: string
  label: string
  description: string
  strength?: string
  optimization?: string
}

interface LayerItem {
  code: string
  label: string
  score?: number
  description: string
  optimization?: string
}

export default function RadarDetail() {
  const [axis, setAxis] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [data, setData] = useState<ReportResp | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useLoad((opts: Record<string, string>) => {
    if (!requireLogin()) return
    setAxis(opts.axis || null)
    const id = opts.taskId
    if (!id) {
      setLoading(false)
      setErr('缺少任务标识，请返回报告页重试。')
      return
    }
    setTaskId(id)
    getReport(id)
      .then(setData)
      .catch((e) => setErr((e as Error)?.message || '报告加载失败，请稍后重试。'))
      .then(() => setLoading(false))
  })

  if (!axis) return null
  const meta = AXIS_META[axis]
  if (!meta) return null

  const section = data
    ? (data as unknown as Record<string, Record<string, unknown>>)[axis]
    : undefined

  const description =
    (section?.description as string) || (section?.narrative as string) || ''
  const label = (section?.label as string) || (section?.primary_label as string) || ''
  const score = section?.score as number | undefined
  const summary = (section?.summary as string) || ''
  const evidence = (section?.evidence as string[]) || []
  const keywords = (section?.keywords as string[]) || []
  const zones = (section?.zones as ZoneItem[]) || []
  const layers = (section?.layers as LayerItem[]) || []

  const hasContent =
    !!description ||
    !!summary ||
    !!label ||
    evidence.length > 0 ||
    keywords.length > 0 ||
    zones.length > 0 ||
    layers.length > 0

  return (
    <View className='rd-page'>
      <BrandHeader
        right={
          <View className='rd-back' onClick={() => Taro.navigateBack()}>
            ← 返回
          </View>
        }
      />
      <AiGeneratedNotice />

      <View className='rd-title'>分享你的美学报告</View>
      <View className='rd-sub'>
        {meta.cn} · {meta.en}
      </View>

      {/* P4 · 大居中卡片 */}
      <View className='rd-card'>
        {loading && <View className='rd-state'>加载中…</View>}
        {!loading && err && <View className='rd-state rd-state--err'>报告加载失败：{err}</View>}
        {!loading && !err && !hasContent && <View className='rd-state'>暂无该维度明细</View>}

        <View className='rd-badge__wrap'>
          <View
            className='rd-badge'
            style={{
              background: `linear-gradient(135deg, ${rgba(meta.accent, 0.33)}, ${rgba(
                meta.accent,
                0.67,
              )})`,
              borderColor: meta.accent,
              boxShadow: `0 8px 20px ${rgba(meta.accent, 0.33)}`,
            }}
          >
            {meta.cn}
          </View>
        </View>

        <View className='rd-label'>{label || meta.cn}</View>
        {score != null && (
          <View className='rd-score' style={{ color: meta.accent }}>
            综合评分 {score}
          </View>
        )}

        {!!description && <View className='rd-desc'>{description}</View>}
        {!!summary && <View className='rd-summary'>{summary}</View>}

        {/* 关键词 / 佐证 */}
        {keywords.length > 0 && (
          <View className='rd-tags'>
            {keywords.map((k) => (
              <Text
                className='rd-tag'
                key={k}
                style={{
                  background: rgba(meta.accent, 0.13),
                  borderColor: rgba(meta.accent, 0.33),
                }}
              >
                {k}
              </Text>
            ))}
          </View>
        )}
        {evidence.length > 0 && (
          <View className='rd-evidence'>
            {evidence.map((e, i) => (
              <View className='rd-evidence__li' key={i}>
                · {e}
              </View>
            ))}
          </View>
        )}

        {/* 分区详情：6 个部位 */}
        {zones.length > 0 && (
          <View className='rd-items'>
            {zones.map((z) => (
              <View className='rd-item' key={z.code}>
                <View className='rd-item__label' style={{ color: meta.accent }}>
                  {z.label}
                </View>
                <View className='rd-item__desc'>{z.description}</View>
                {(!!z.strength || !!z.optimization) && (
                  <View className='rd-item__note'>
                    {!!z.strength && <View>· 优势：{z.strength}</View>}
                    {!!z.optimization && <View>· 优化：{z.optimization}</View>}
                  </View>
                )}
              </View>
            ))}
          </View>
        )}

        {/* 分层详情：4 层带独立评分 */}
        {layers.length > 0 && (
          <View className='rd-items'>
            {layers.map((l) => (
              <View className='rd-item' key={l.code}>
                <View className='rd-item__row'>
                  <Text className='rd-item__label' style={{ color: meta.accent }}>
                    {l.label}
                  </Text>
                  {l.score != null && (
                    <Text className='rd-item__score' style={{ color: meta.accent }}>
                      {l.score}
                    </Text>
                  )}
                </View>
                <View className='rd-item__desc'>{l.description}</View>
                {!!l.optimization && (
                  <View className='rd-item__note'>· 优化：{l.optimization}</View>
                )}
              </View>
            ))}
          </View>
        )}

        {/* 二维码占位：与 P4 一致的分享位 */}
        <View className='rd-qr'>
          <View className='rd-qr__box'>二维码</View>
          <View className='rd-qr__tip'>扫码进入小程序 · 复制体验</View>
        </View>
      </View>

      {/* CTA：与 H5 的详情页一致，导出 + 预约两个入口 */}
      <View className='rd-cta'>
        {data && <ReportExport data={data} axis={axis} />}
        <Button
          className='rd-cta__btn'
          onClick={() =>
            Taro.navigateTo({
              url: `/pages/booking/index?taskId=${taskId || ''}&source=radar-detail`,
            })
          }
        >
          预约到店面诊
        </Button>
      </View>

      <DisclaimerFooter />
    </View>
  )
}
