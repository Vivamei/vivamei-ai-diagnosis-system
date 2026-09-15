import { useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'

import { getReport, ReportResp } from '@/api/analyze'
import { ApiError } from '@/api/client'
import { AiBadge } from '@/components/AiBadge'
import { AiGeneratedNotice } from '@/components/AiGeneratedNotice'
import { BrandHeader } from '@/components/BrandHeader'
import { DisclaimerFooter } from '@/components/DisclaimerFooter'
import { RadarChart } from '@/components/RadarChart'
import { ReportExport } from '@/components/ReportExport'
import { COPY } from '@/config'
import { requireLogin } from '@/utils/nav'
import './index.css'

interface ZoneItem {
  code: string
  label: string
  score?: number
  status?: string
  description: string
  strength?: string
  optimization?: string
}

interface LayerItem {
  code: string
  label: string
  score?: number
  status?: string
  description: string
  optimization?: string
}

const LAYER_COLOR: Record<string, string> = {
  skin: '#e8b04f',
  subcutis: '#d47a6a',
  fascia: '#88b09a',
  bone: '#c8a376',
}

// 3 类衰老相型（对齐报价单：骨相 / 肉相 / 皮相）
const STYPE_STAGES = [
  { key: 'skin', label: '皮相', aliases: ['skin', '皮相', '皮相主导'] },
  { key: 'flesh', label: '肉相', aliases: ['flesh', '肉相', '肉相主导'] },
  { key: 'bone', label: '骨相', aliases: ['bone', '骨相', '骨相主导'] },
]

// 分相星级项（贵方 style_reference.composition，后端已把 soft_tissue 映射成 flesh）
interface CompositionItem {
  label?: string
  stars?: number
  max_stars?: number
}

// 分相占比 → 星级：以三相中的最高占比为满 5 星，其余按比例折算（至少 1 星）。
function ratioToStars(ratio: number, maxRatio: number): number {
  if (!(maxRatio > 0)) return 1
  return Math.max(1, Math.min(5, Math.round((ratio / maxRatio) * 5)))
}

export default function Report() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [data, setData] = useState<ReportResp | null>(null)
  const [err, setErr] = useState<{ code: string; message: string; requestId?: string } | null>(
    null,
  )

  useLoad((opts: Record<string, string>) => {
    if (!requireLogin()) return
    const id = opts.taskId
    if (!id) {
      setErr({ code: 'MISSING_TASK_ID', message: '缺少任务标识，请重新发起分析。' })
      return
    }
    setTaskId(id)
    getReport(id)
      .then(setData)
      .catch((e) => {
        const api = e instanceof ApiError ? e : null
        setErr({
          code: api?.code || 'REPORT_LOAD_ERROR',
          message: (e as Error)?.message || '报告加载失败，请稍后重试。',
          requestId: api?.requestId,
        })
      })
  })

  if (err) {
    return (
      <View className='rp-page'>
        <BrandHeader />
        <View className='rp-err'>
          <View className='rp-err__title'>报告加载失败</View>
          <View className='rp-err__msg'>{err.message}</View>
          <View className='rp-err__code'>
            错误码：{err.code}
            {err.requestId ? ` · 请求号：${err.requestId}` : ''}
          </View>
          <View className='rp-err__actions'>
            {taskId && (
              <Button
                className='rp-err__btn'
                onClick={() => Taro.redirectTo({ url: `/pages/report/index?taskId=${taskId}` })}
              >
                重试
              </Button>
            )}
            <Button
              className='rp-err__btn rp-err__btn--ghost'
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}
            >
              返回首页
            </Button>
          </View>
        </View>
      </View>
    )
  }

  if (!data) {
    return (
      <View className='rp-page'>
        <View className='rp-loading'>报告加载中…</View>
      </View>
    )
  }

  const stypePrimary = (data.stype.primary as string) || (data.stype.label as string) || ''
  const stypeLabel = (data.stype.label as string) || ''
  const stypeText =
    (data.stype.description as string) || (data.stype.narrative as string) || ''
  const stypeEvidence = (data.stype.evidence as string[]) || []
  const stypeRatios = (data.stype.ratios as Record<string, number>) || null
  const stypeComposition =
    (data.stype.composition as Record<string, CompositionItem>) || null
  const stypeScore = data.stype.score as number | undefined

  const styleLabel =
    (data.style.label as string) || (data.style.primary_label as string) || ''
  const styleText =
    (data.style.description as string) || (data.style.narrative as string) || ''
  const styleKeywords = (data.style.keywords as string[]) || []
  const styleScore = data.style.score as number | undefined

  const subzoneSummary = (data.subzone.summary as string) || ''
  const subzoneZones = (data.subzone.zones as ZoneItem[]) || []
  const subzoneScore = data.subzone.score as number | undefined

  const structSummary = (data.struct.summary as string) || ''
  const structLayers = (data.struct.layers as LayerItem[]) || []
  const structScore = data.struct.score as number | undefined

  // 贵方新口径：radarScores 是轴长（衰老差距），越小越年轻；图下方 4S 数值另取
  // state_values（状态分，越高越年轻）。两者都由贵方直接给出，本方不换算。
  // 分型不参与衰老计算，其轴值固定在高位，故文案需单独说明。
  // 旧口径（radar_semantics 缺省）雷达图仍是得分，越高越好。
  const agingExposure =
    data.radar_semantics === 'aging_exposure' ||
    data.radar_semantics === 'four_s_state_gap_index'

  const aOpt = data.aesthetic_optimization || {}
  const projectDirections = data.project_directions || []
  const mappedDirections = data.mapped_project_directions || []

  const isActiveStage = (aliases: string[]) =>
    aliases.some((a) => stypePrimary.toLowerCase().includes(a.toLowerCase()))

  // 星级行优先用贵方直接给的三相星级（composition），此时星最多的一相即主导相；
  // 旧版报告只有占比（ratios），仍按最高占比折算 5 星。
  const compositionRows = stypeComposition
    ? STYPE_STAGES.map((s) => ({ stage: s, item: stypeComposition[s.key] }))
        .filter((r) => typeof r.item?.stars === 'number')
        .sort((a, b) => (b.item.stars ?? 0) - (a.item.stars ?? 0))
    : []
  const maxRatio = stypeRatios
    ? Math.max(...STYPE_STAGES.map((s) => stypeRatios[s.key] ?? 0), 0)
    : 0

  let starRows: { key: string; label: string; stars: number; active: boolean }[] | null = null
  if (compositionRows.length > 0) {
    const top = compositionRows[0].item.stars ?? 0
    starRows = compositionRows.map(({ stage, item }) => ({
      key: stage.key,
      label: item.label || stage.label,
      stars: item.stars ?? 0,
      active: (item.stars ?? 0) === top,
    }))
  } else if (stypeRatios) {
    starRows = STYPE_STAGES.map((s) => ({ stage: s, ratio: stypeRatios[s.key] ?? 0 }))
      .sort((a, b) => b.ratio - a.ratio)
      .map(({ stage, ratio }) => ({
        key: stage.key,
        label: stage.label,
        stars: ratioToStars(ratio, maxRatio),
        active: isActiveStage(stage.aliases),
      }))
  }

  return (
    <View className='rp-page'>
      <BrandHeader right={<AiBadge />} />
      <AiGeneratedNotice />

      {/* P1 · 4S 雷达图 */}
      <View className='rp-sec rp-sec--light'>
        <View className='rp-radar__cn'>{COPY.brandName} 4S 雷达图</View>
        <View className='rp-radar__en'>
          {agingExposure ? '图形越小越年轻 · 分型不参与衰老评估' : '四维评估体系 · 精准定位衰老维度'}
        </View>
        <RadarChart
          scores={data.radarScores}
          legendScores={data.state_values}
          max={data.radar_max ?? 100}
          onAxisClick={(a) =>
            Taro.navigateTo({ url: `/pages/radar-detail/index?taskId=${taskId}&axis=${a}` })
          }
        />
      </View>

      {/* P2 · 分型诊断 */}
      <View className='rp-sec'>
        <View className='rp-title'>
          <Text className='rp-title__cn'>分型诊断</Text>
          <Text className='rp-title__en'>· Style</Text>
          {typeof styleScore === 'number' && (
            <Text className='rp-title__score'>得分 {styleScore}</Text>
          )}
        </View>
        {!!styleLabel && <View className='rp-label'>{styleLabel}</View>}
        <View className='rp-text'>{styleText}</View>
        {styleKeywords.length > 0 && (
          <View className='rp-tags'>
            {styleKeywords.map((k) => (
              <Text className='rp-tag' key={k}>
                {k}
              </Text>
            ))}
          </View>
        )}
      </View>

      {/* P2 · 分相诊断 */}
      <View className='rp-sec'>
        <View className='rp-title'>
          <Text className='rp-title__cn'>分相诊断</Text>
          <Text className='rp-title__en'>· Stype</Text>
          {typeof stypeScore === 'number' && (
            <Text className='rp-title__score'>得分 {stypeScore}</Text>
          )}
        </View>

        {starRows ? (
          <View className='rp-stars'>
            {starRows.map((row) => (
              <View className='rp-star-row' key={row.key}>
                <Text
                  className={`rp-star-row__label ${row.active ? 'rp-star-row__label--active' : ''}`}
                >
                  {row.label}
                </Text>
                <Text className='rp-star'>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <Text className={n <= row.stars ? 'rp-star--on' : ''} key={n}>
                      ★
                    </Text>
                  ))}
                </Text>
              </View>
            ))}
          </View>
        ) : (
          <View className='rp-stage'>
            {STYPE_STAGES.map((s, i) => {
              const active = isActiveStage(s.aliases)
              const isLast = i === STYPE_STAGES.length - 1
              return (
                <View className={`rp-stage__seg ${isLast ? 'rp-stage__seg--last' : ''}`} key={s.key}>
                  <View className='rp-stage__node'>
                    <View className={`rp-stage__dot ${active ? 'rp-stage__dot--active' : ''}`}>
                      {i + 1}
                    </View>
                    <View className={`rp-stage__name ${active ? 'rp-stage__name--active' : ''}`}>
                      {s.label}
                    </View>
                  </View>
                  {!isLast && <View className='rp-stage__line' />}
                </View>
              )
            })}
          </View>
        )}

        <View className='rp-label'>{stypeLabel}</View>
        <View className='rp-text'>{stypeText}</View>
        {stypeEvidence.map((e, i) => (
          <View className='rp-li' key={i}>
            · {e}
          </View>
        ))}
      </View>

      {/* P3 · 分区评估 */}
      <View className='rp-sec'>
        <View className='rp-title'>
          <Text className='rp-title__cn'>分区评估</Text>
          <Text className='rp-title__en'>· Subzone</Text>
          {typeof subzoneScore === 'number' && (
            <Text className='rp-title__score'>得分 {subzoneScore}</Text>
          )}
        </View>
        <View className='rp-hint'>按美学分区，逐单位精准诊断</View>
        {!!subzoneSummary && <View className='rp-summary'>{subzoneSummary}</View>}
        <View className='rp-zones'>
          {subzoneZones.slice(0, 6).map((z) => (
            <View className='rp-zone' key={z.code}>
              <View className='rp-zone__inner'>
                <View className='rp-zone__head'>
                  <Text className='rp-zone__label'>{z.label}</Text>
                  {typeof z.score === 'number' && (
                    <Text className='rp-zone__score'>{z.score}</Text>
                  )}
                </View>
                <View className='rp-zone__desc'>{z.description}</View>
                {!!z.strength && <View className='rp-zone__good'>优势 · {z.strength}</View>}
                {!!z.optimization && <View className='rp-zone__opt'>优化 · {z.optimization}</View>}
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* P3 · 分层评估 */}
      <View className='rp-sec'>
        <View className='rp-title'>
          <Text className='rp-title__cn'>分层评估</Text>
          <Text className='rp-title__en'>· Struct</Text>
          {typeof structScore === 'number' && (
            <Text className='rp-title__score'>得分 {structScore}</Text>
          )}
        </View>
        <View className='rp-hint'>按结构层次评估，指导分层结构干预</View>
        {!!structSummary && <View className='rp-summary'>{structSummary}</View>}
        {structLayers.map((l) => {
          const color = LAYER_COLOR[l.code] || '#c8a376'
          const pct = Math.max(0, Math.min(100, l.score ?? 0))
          return (
            <View className='rp-layer' key={l.code}>
              <View className='rp-layer__row'>
                <Text className='rp-layer__name'>{l.label}</Text>
                <Text className='rp-layer__score' style={{ color }}>
                  {l.score ?? '—'}
                </Text>
              </View>
              <View className='rp-layer__bar'>
                <View
                  className='rp-layer__fill'
                  style={{ width: `${pct}%`, background: color }}
                />
              </View>
              {!!(l.status || l.description) && (
                <View className='rp-layer__note'>{l.status || l.description}</View>
              )}
              {!!l.optimization && <View className='rp-layer__opt'>优化 · {l.optimization}</View>}
            </View>
          )
        })}
      </View>

      {/* 美学优化方向 */}
      <View className='rp-opt'>
        <View className='rp-opt__title'>美学优化方向</View>
        <View className='rp-opt__text'>{aOpt.summary || data.optimization}</View>
        {(aOpt.directions || []).map((d, i) => (
          <View className='rp-opt__li' key={i}>
            · {d}
          </View>
        ))}
      </View>

      {projectDirections.length > 0 && (
        <View className='rp-tags'>
          {projectDirections.map((t) => (
            <Text className='rp-tag rp-tag--light' key={t}>
              {t}
            </Text>
          ))}
        </View>
      )}

      {mappedDirections.map((m, i) => (
        <View className='rp-map' key={i}>
          <View className='rp-map__title'>{m.display_title || m.direction}</View>
          {!!m.safe_description && <View className='rp-map__desc'>{m.safe_description}</View>}
          {!!m.consult_note && <View className='rp-map__note'>{m.consult_note}</View>}
        </View>
      ))}

      {/* 导出：小程序没有 DOM，走 Canvas 画报告长图后存相册（等效 H5 的 ReportExport） */}
      <ReportExport data={data} />

      {/* CTA：带上 taskId，预约单能关联到这份报告 */}
      <View className='rp-lead'>{COPY.leadText}</View>
      <Button
        className='rp-cta'
        onClick={() =>
          Taro.navigateTo({ url: `/pages/booking/index?taskId=${taskId}&source=report` })
        }
      >
        {COPY.ctaReport}
      </Button>

      <DisclaimerFooter />
    </View>
  )
}
