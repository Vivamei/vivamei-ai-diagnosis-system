import { useState } from 'react'
import { Button, Canvas, View } from '@tarojs/components'
import Taro from '@tarojs/taro'

import type { ReportResp } from '@/api/analyze'
import { COPY } from '@/config'
import './ReportExport.css'

// H5 的 ReportExport 用 html2canvas 把 DOM 截成长图；小程序没有 DOM 也没有 html2canvas，
// 等效做法是用 Canvas 按同一套排版把报告重绘一遍，再 canvasToTempFilePath + 存相册。
// 视觉口径（配色、字号层级、免责声明、右下角水印）与 H5 保持一致，不做弱化。

const AI_GENERATED_NOTICE = '本服务为AI生成内容，结果仅供参考'
const WATERMARK = 'AI生成 · 仅供参考'
const CANVAS_ID = 'venus-report-export'

const W = 320 // 设计宽（CSS px），导出时按 dpr 放大保证清晰度
const PAD = 20
const CONTENT_W = W - PAD * 2
const BG = '#fdfaf5'

const AXIS_META: Record<string, { cn: string; en: string; accent: string }> = {
  stype: { cn: '分相', en: 'Stype', accent: '#c99048' },
  style: { cn: '分型', en: 'Style', accent: '#cc5f4f' },
  subzone: { cn: '分区', en: 'Subzone', accent: '#7a8f5a' },
  struct: { cn: '分层', en: 'Struct', accent: '#5a7896' },
}
const AXES = ['style', 'stype', 'subzone', 'struct']

/**
 * 估算文字宽度。canvas 的 measureText 要等 context 就绪、还得跨端对齐，
 * 这里按「中日韩全角 ≈ 1 个字号、其余 ≈ 0.55 个字号」估算，误差足够排版用，
 * 也让「先算高度再建 canvas」这一步可以纯同步完成。
 */
function textWidth(s: string, size: number): number {
  let w = 0
  for (const ch of s) w += /[⺀-￯]/.test(ch) ? size : size * 0.55
  return w
}

function wrap(text: string, size: number, maxWidth: number): string[] {
  const lines: string[] = []
  for (const para of String(text).split('\n')) {
    let cur = ''
    let curW = 0
    for (const ch of para) {
      const cw = textWidth(ch, size)
      if (curW + cw > maxWidth && cur) {
        lines.push(cur)
        cur = ''
        curW = 0
      }
      cur += ch
      curW += cw
    }
    lines.push(cur)
  }
  return lines
}

interface Op {
  text: string
  size: number
  bold?: boolean
  color: string
  align?: 'left' | 'center'
  lh: number
  gap: number // 与上一块的间距
  rule?: string // 该块下方画一条横线（颜色）
}

const str = (v: unknown): string => (typeof v === 'string' ? v : '')
const num = (v: unknown): number | undefined => (typeof v === 'number' ? v : undefined)

function buildOps(data: ReportResp, axis?: string | null): Op[] {
  const ops: Op[] = []
  const push = (o: Partial<Op> & { text: string }) =>
    ops.push({ size: 13, color: '#3a342c', lh: 21, gap: 8, ...o })

  push({ text: COPY.brandName, size: 20, bold: true, color: '#3a342c', lh: 28, gap: 0, align: 'center' })
  push({ text: COPY.brandSubtitle, size: 10, color: '#a8855a', lh: 16, gap: 4, align: 'center' })
  push({ text: AI_GENERATED_NOTICE, size: 13, bold: true, color: '#80551f', lh: 22, gap: 10, align: 'center' })
  push({ text: '', size: 1, color: BG, lh: 1, gap: 10, rule: '#e8d5b3' })

  // 4S 数值一行（H5 报告页雷达图下方的 2×2 图例，长图里压成一行更省高度）
  const legend = data.state_values || data.radarScores
  const legendLine = AXES.map((k) => `${AXIS_META[k].cn} ${legend[k] ?? '—'}`).join('    ')
  push({ text: legendLine, size: 13, bold: true, color: '#a8855a', lh: 22, gap: 12, align: 'center' })

  const wanted = axis && AXIS_META[axis] ? [axis] : AXES
  for (const k of wanted) {
    const meta = AXIS_META[k]
    const sec = (data as unknown as Record<string, Record<string, unknown>>)[k] || {}
    const score = num(sec.score)
    push({
      text: `${meta.cn} · ${meta.en}${score != null ? `　得分 ${score}` : ''}`,
      size: 15,
      bold: true,
      color: meta.accent,
      lh: 24,
      gap: 16,
    })
    const label = str(sec.label) || str(sec.primary_label)
    if (label) push({ text: label, size: 14, bold: true, lh: 22, gap: 6 })
    const desc = str(sec.description) || str(sec.narrative) || str(sec.summary)
    if (desc) push({ text: desc, size: 13, color: '#5f5749', lh: 21, gap: 6 })

    const keywords = (sec.keywords as string[]) || []
    if (keywords.length) push({ text: keywords.join(' · '), size: 12, color: '#a8855a', lh: 20, gap: 6 })
    for (const e of (sec.evidence as string[]) || []) {
      push({ text: `· ${e}`, size: 12, color: '#8c7e6e', lh: 20, gap: 4 })
    }
    for (const z of (sec.zones as { label?: string; description?: string }[]) || []) {
      push({ text: `· ${z.label || ''}：${z.description || ''}`, size: 12, color: '#8c7e6e', lh: 20, gap: 4 })
    }
    for (const l of (sec.layers as { label?: string; score?: number; description?: string }[]) || []) {
      const s = typeof l.score === 'number' ? ` ${l.score}` : ''
      push({ text: `· ${l.label || ''}${s}：${l.description || ''}`, size: 12, color: '#8c7e6e', lh: 20, gap: 4 })
    }
  }

  const aOpt = data.aesthetic_optimization || {}
  const optText = aOpt.summary || data.optimization
  if (optText) {
    push({ text: '美学优化方向', size: 15, bold: true, color: '#a8855a', lh: 24, gap: 18 })
    push({ text: optText, size: 13, color: '#5f5749', lh: 21, gap: 6 })
    for (const d of aOpt.directions || []) {
      push({ text: `· ${d}`, size: 12, color: '#8c7e6e', lh: 20, gap: 4 })
    }
  }

  push({ text: '', size: 1, color: BG, lh: 1, gap: 18, rule: '#e8d5b3' })
  push({ text: COPY.reportDisclaimerLine1, size: 11, color: '#c5b9aa', lh: 18, gap: 10, align: 'center' })
  push({ text: COPY.reportDisclaimerLine2, size: 11, color: '#c5b9aa', lh: 18, gap: 2, align: 'center' })
  return ops
}

/** 排版：把每个 op 折行并算出 y 坐标，同时得到画布总高。 */
function layout(ops: Op[]) {
  const placed: { op: Op; lines: string[]; y: number }[] = []
  let y = PAD
  for (const op of ops) {
    y += op.gap
    const lines = op.text ? wrap(op.text, op.size, CONTENT_W) : []
    placed.push({ op, lines, y })
    y += lines.length * op.lh
    if (op.rule) y += 1
  }
  return { placed, height: Math.ceil(y + PAD + 18) } // 尾部留出水印行
}

interface Props {
  data: ReportResp
  /** 只导出某一个维度（雷达图详情页用），缺省导出完整报告。 */
  axis?: string | null
}

export function ReportExport({ data, axis }: Props) {
  const [busy, setBusy] = useState(false)
  const [size, setSize] = useState<{ w: number; h: number } | null>(null)

  const run = async () => {
    if (busy) return
    setBusy(true)
    try {
      const { placed, height } = layout(buildOps(data, axis))
      // Canvas 元素得先按目标高度渲染出来，画布尺寸才够；setState 后等一帧再画。
      setSize({ w: W, h: height })
      await new Promise((r) => setTimeout(r, 60))

      const ctx = Taro.createCanvasContext(CANVAS_ID)
      ctx.setFillStyle(BG)
      ctx.fillRect(0, 0, W, height)
      ctx.setTextBaseline('top')

      for (const { op, lines, y } of placed) {
        if (op.rule) {
          ctx.setStrokeStyle(op.rule)
          ctx.setLineWidth(1)
          ctx.beginPath()
          ctx.moveTo(PAD, y + 0.5)
          ctx.lineTo(W - PAD, y + 0.5)
          ctx.stroke()
        }
        if (!lines.length) continue
        ctx.font = `${op.bold ? 'bold' : 'normal'} ${op.size}px sans-serif`
        ctx.setFillStyle(op.color)
        ctx.setTextAlign(op.align === 'center' ? 'center' : 'left')
        const x = op.align === 'center' ? W / 2 : PAD
        lines.forEach((ln, i) => ctx.fillText(ln, x, y + i * op.lh))
      }

      // 右下角水印，与 H5 的 rgba(58,52,44,0.5) / 14px 同款
      ctx.font = 'normal 12px sans-serif'
      ctx.setFillStyle('rgba(58,52,44,0.5)')
      ctx.setTextAlign('right')
      ctx.fillText(WATERMARK, W - PAD, height - PAD - 4)

      await new Promise<void>((resolve) => ctx.draw(false, () => resolve()))

      const { tempFilePath } = await Taro.canvasToTempFilePath({
        canvasId: CANVAS_ID,
        // 按设备像素比放大，否则存到相册是模糊的
        destWidth: W * (Taro.getSystemInfoSync().pixelRatio || 2),
        destHeight: height * (Taro.getSystemInfoSync().pixelRatio || 2),
      })

      await saveToAlbum(tempFilePath)
    } catch (e) {
      console.error('[report-export] 导出失败', e)
      Taro.showToast({ title: '生成失败，请稍后重试', icon: 'none' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <View className='rpx'>
      <Button className='rpx-btn' disabled={busy} onClick={run}>
        {busy ? '生成中…' : '保存报告长图'}
      </Button>
      {/* 离屏画布：只用于出图，不参与页面布局 */}
      {size && (
        <Canvas
          className='rpx-canvas'
          canvasId={CANVAS_ID}
          id={CANVAS_ID}
          style={{ width: `${size.w}px`, height: `${size.h}px` }}
        />
      )}
    </View>
  )
}

/**
 * 存相册。用户点过「拒绝」后 saveImageToPhotosAlbum 会直接失败且不再弹授权框，
 * 必须自己引导去设置页打开，否则用户只会看到一次性失败、无从恢复。
 */
async function saveToAlbum(filePath: string) {
  try {
    await Taro.saveImageToPhotosAlbum({ filePath })
    Taro.showToast({ title: '已保存到相册', icon: 'success' })
  } catch (e) {
    const msg = String((e as { errMsg?: string })?.errMsg || '')
    if (!/auth|deny|authorize/i.test(msg)) {
      Taro.showToast({ title: '保存失败，请稍后重试', icon: 'none' })
      return
    }
    const { confirm } = await Taro.showModal({
      title: '需要相册权限',
      content: '保存报告长图需要「保存到相册」权限，去设置里开启？',
      confirmText: '去设置',
    })
    if (!confirm) return
    const res = await Taro.openSetting()
    if (res.authSetting['scope.writePhotosAlbum']) {
      await Taro.saveImageToPhotosAlbum({ filePath })
      Taro.showToast({ title: '已保存到相册', icon: 'success' })
    }
  }
}
