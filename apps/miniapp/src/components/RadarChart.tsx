import { useEffect, useState } from 'react'
import { Canvas, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'

import type { Phase } from '@/hooks/useAnalyzeStream'
import './RadarChart.css'

// 顶点/图例色（对齐 H5：分相 橙、分型 红、分区 绿、分层 蓝）
const AXIS_COLORS: Record<Phase, string> = {
  stype: '#c99048',
  style: '#cc5f4f',
  subzone: '#7a8f5a',
  struct: '#5a7896',
}

// 4 轴：上 分相 / 左 分型 / 右 分区 / 下 分层
const AXIS_META: Record<Phase, { cn: string; en: string; angle: number }> = {
  stype: { cn: '分相', en: 'Stype', angle: -90 },
  style: { cn: '分型', en: 'Style', angle: 180 },
  subzone: { cn: '分区', en: 'Subzone', angle: 0 },
  struct: { cn: '分层', en: 'Struct', angle: 90 },
}

// 图例展示顺序（2×2）
const AXES: Phase[] = ['stype', 'style', 'subzone', 'struct']
// 多边形连线顺序（几何顺时针，避免连出蝴蝶结）
const POLY_AXES: Phase[] = ['stype', 'subzone', 'struct', 'style']

const W = 300
const H = 280
const CX = W / 2
const CY = H / 2
const R = 84
const CANVAS_ID = 'venus-radar'

const polar = (angleDeg: number, r: number) => {
  const rad = (angleDeg * Math.PI) / 180
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) }
}

/**
 * 居中绘制一段带字距的文字。canvas 没有 letter-spacing，只能逐字画，
 * 否则 H5 轴标签 letterSpacing="1" 的疏朗感在小程序里会丢掉，英文标签看起来更挤。
 * 传入的 cx 是这段文字的中心，内部按总宽反推起点并临时切成左对齐。
 */
const fillTextTracked = (
  ctx: Taro.CanvasContext,
  text: string,
  cx: number,
  cy: number,
  tracking: number,
) => {
  const chars = text.split('')
  const widths = chars.map((c) => ctx.measureText(c).width)
  const total = widths.reduce((a, b) => a + b, 0) + tracking * (chars.length - 1)
  let x = cx - total / 2
  ctx.setTextAlign('left')
  chars.forEach((c, i) => {
    ctx.fillText(c, x, cy)
    x += widths[i] + tracking
  })
  ctx.setTextAlign('center')
}

// 轴标签的点击热区（以标签中心为原点的半宽/半高）。H5 是给标签 <g> 绑 onClick，
// canvas 里没有子元素可绑，只能按坐标命中；尺寸取两行文字外扩一圈，便于手指点。
const LABEL_HIT_W = 26
const LABEL_HIT_H = 18

interface CanvasTouchEvent {
  touches?: { x: number; y: number }[]
  changedTouches?: { x: number; y: number }[]
}

interface Props {
  scores: Record<Phase, number>
  // 图下方 2×2 展示的数值（贵方 radar_chart.state_values，状态分，越高越年轻）。
  // 与 scores（轴长，越小越年轻）是两套口径；缺省时回落到 scores。
  legendScores?: Record<Phase, number> | null
  // 刻度上限，由贵方 radar_chart.max 给出；缺省 100（旧口径得分制）
  max?: number
  onAxisClick?: (axis: Phase) => void
}

export function RadarChart({ scores, legendScores, max = 100, onAxisClick }: Props) {
  const [height, setHeight] = useState(H)
  const [scale, setScale] = useState(0)
  const legend = legendScores ?? scores

  // 小程序不支持内联 SVG，雷达图改用 canvas 绘制。canvas 的绘制坐标系是 CSS px，
  // 所以先量出实际渲染宽度，再按 300 的设计宽等比缩放，宽屏机型才不会画出留白。
  useEffect(() => {
    Taro.createSelectorQuery()
      .select(`#${CANVAS_ID}`)
      .boundingClientRect((rect) => {
        const w = (rect as { width?: number } | null)?.width || W
        setHeight((w * H) / W)
        setScale(w / W)
      })
      .exec()
  }, [])

  const { stype, style, subzone, struct } = scores

  useEffect(() => {
    if (!scale) return
    const ctx = Taro.createCanvasContext(CANVAS_ID)
    ctx.scale(scale, scale)

    const scaleMax = max > 0 ? max : 100
    const vertex = (k: Phase) =>
      polar(
        AXIS_META[k].angle,
        (R * Math.max(0, Math.min(scaleMax, scores[k]))) / scaleMax,
      )

    // 5 层圆环刻度（对应 max 的 20% / 40% / 60% / 80% / 100%）
    // 内圈比外圈略深（0.55 → 0.70），H5 用 strokeOpacity 做，canvas 只能把透明度写进 rgba。
    ctx.setLineWidth(1)
    ;[1.0, 0.8, 0.6, 0.4, 0.2].forEach((f) => {
      ctx.setStrokeStyle(`rgba(230,221,208,${(0.55 + (1 - f) * 0.15).toFixed(3)})`)
      ctx.beginPath()
      ctx.arc(CX, CY, R * f, 0, Math.PI * 2)
      ctx.stroke()
    })

    // 轴向虚线引导
    ctx.setLineDash([2, 3], 0)
    ctx.setLineWidth(0.8)
    ctx.setStrokeStyle('rgba(216,204,187,0.6)')
    AXES.forEach((k) => {
      const p = polar(AXIS_META[k].angle, R)
      ctx.beginPath()
      ctx.moveTo(CX, CY)
      ctx.lineTo(p.x, p.y)
      ctx.stroke()
    })
    ctx.setLineDash([], 0)

    // 数据菱形（透明底 + 金色描边）
    ctx.beginPath()
    POLY_AXES.forEach((k, i) => {
      const p = vertex(k)
      if (i === 0) ctx.moveTo(p.x, p.y)
      else ctx.lineTo(p.x, p.y)
    })
    ctx.closePath()
    ctx.setFillStyle('rgba(200,163,118,0.15)')
    ctx.fill()
    ctx.setLineJoin('round')
    ctx.setLineWidth(1.8)
    ctx.setStrokeStyle('#a37c40')
    ctx.stroke()

    // 顶点彩色小圆
    AXES.forEach((k) => {
      const p = vertex(k)
      ctx.beginPath()
      ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2)
      ctx.setFillStyle(AXIS_COLORS[k])
      ctx.fill()
      ctx.setLineWidth(1.6)
      ctx.setStrokeStyle('#ffffff')
      ctx.stroke()
    })

    // 外侧轴标签（CN 在上、EN 在下，避免长英文溢出画布）
    ctx.setTextAlign('center')
    ctx.setTextBaseline('middle')
    AXES.forEach((k) => {
      const m = AXIS_META[k]
      const isVertical = m.angle === -90 || m.angle === 90
      const base = polar(m.angle, isVertical ? R + 24 : R + 22)
      // 中文用 700 字重，canvas 只能通过 font 简写指定，setFontSize 表达不了粗细
      ctx.font = 'bold 13px sans-serif'
      ctx.setFillStyle('#3a342c')
      ctx.fillText(m.cn, base.x, base.y - 7)
      ctx.font = 'normal 10px sans-serif'
      ctx.setFillStyle('#8c7e6e')
      fillTextTracked(ctx, m.en, base.x, base.y + 8, 1)
    })

    ctx.draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scale, max, stype, style, subzone, struct])

  // 触点坐标是渲染尺寸下的 CSS px，先除以 scale 换回 300×280 设计坐标系再做命中判断。
  const handleCanvasTouch = (e: CanvasTouchEvent) => {
    if (!onAxisClick || !scale) return
    const t = e.touches?.[0] || e.changedTouches?.[0]
    if (!t) return
    const x = t.x / scale
    const y = t.y / scale
    const hit = AXES.find((k) => {
      const m = AXIS_META[k]
      const isVertical = m.angle === -90 || m.angle === 90
      const p = polar(m.angle, isVertical ? R + 24 : R + 22)
      return Math.abs(x - p.x) <= LABEL_HIT_W && Math.abs(y - p.y) <= LABEL_HIT_H
    })
    if (hit) onAxisClick(hit)
  }

  return (
    <View>
      <Canvas
        className='rc-canvas'
        canvasId={CANVAS_ID}
        id={CANVAS_ID}
        style={{ height: `${height}px` }}
        onTouchStart={handleCanvasTouch}
      />

      {onAxisClick && <View className='rc-hint'>点击任一维度查看该维度明细</View>}

      <View className='rc-legend'>
        {AXES.map((k) => (
          <View className='rc-cell' key={k}>
            <View className='rc-cell__inner' onClick={() => onAxisClick?.(k)}>
              <View className='rc-cell__left'>
                <View className='rc-dot' style={{ background: AXIS_COLORS[k] }} />
                <Text className='rc-name'>{AXIS_META[k].cn}</Text>
              </View>
              <View className='rc-cell__right'>
                <Text className='rc-score'>{legend[k]}</Text>
                {onAxisClick && <Text className='rc-chev'>›</Text>}
              </View>
            </View>
          </View>
        ))}
      </View>
    </View>
  )
}
