import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'

import './Legal.css'

// 与 apps/web/src/pages/legal/LegalLayout.tsx 一一对应：同样的 hero 渐变头、版本徽章、
// 目录卡、带序号的小节标题、圆点列表、表格与提示条。H5 是内联样式，这里落到 Legal.css。

export interface TocItem {
  id: string
  label: string
}

/** 一段正文；bold 的部分单独拆出来，小程序里没有 <strong> 可用。 */
export type Segment = string | { b: string }

export type Block =
  | { type: 'p'; text: Segment[] }
  | { type: 'list'; items: Segment[][] }
  | { type: 'table'; headers: string[]; rows: Segment[][][] }
  | { type: 'callout'; tone: 'info' | 'warning'; text: Segment[] }

export interface Section {
  id: string
  index: string
  title: string
  blocks: Block[]
}

export interface LegalDoc {
  title: string
  version: string
  effectiveDate: string
  contactEmail: string
  brand: string
  toc: TocItem[]
  sections: Section[]
}

function Rich({ segs, className }: { segs: Segment[]; className?: string }) {
  return (
    <Text className={className}>
      {segs.map((s, i) =>
        typeof s === 'string' ? (
          <Text key={i}>{s}</Text>
        ) : (
          <Text className='lg-b' key={i}>
            {s.b}
          </Text>
        ),
      )}
    </Text>
  )
}

function Blocks({ blocks }: { blocks: Block[] }) {
  return (
    <View>
      {blocks.map((b, i) => {
        if (b.type === 'p') return <Rich className='lg-p' segs={b.text} key={i} />
        if (b.type === 'list') {
          return (
            <View className='lg-list' key={i}>
              {b.items.map((it, j) => (
                <View className='lg-item' key={j}>
                  <View className='lg-item__dot' />
                  <Rich className='lg-item__text' segs={it} />
                </View>
              ))}
            </View>
          )
        }
        if (b.type === 'callout') {
          return (
            <View className={`lg-callout lg-callout--${b.tone}`} key={i}>
              <Rich segs={b.text} />
            </View>
          )
        }
        return (
          <View className='lg-table' key={i}>
            <View className='lg-tr lg-tr--head'>
              {b.headers.map((h) => (
                <Text className='lg-th' key={h}>
                  {h}
                </Text>
              ))}
            </View>
            {b.rows.map((row, j) => (
              <View className='lg-tr' key={j}>
                {row.map((cell, k) => (
                  <Rich className='lg-td' segs={cell} key={k} />
                ))}
              </View>
            ))}
          </View>
        )
      })}
    </View>
  )
}

export function LegalPage({ doc }: { doc: LegalDoc }) {
  return (
    <View className='lg-page'>
      <View className='lg-hero'>
        <View className='lg-hero__brand'>{doc.brand}</View>
        <View className='lg-hero__title'>{doc.title}</View>
        <View className='lg-hero__divider' />
        <View className='lg-hero__badges'>
          <Text className='lg-badge'>版本 {doc.version}</Text>
          <Text className='lg-badge'>生效日期 {doc.effectiveDate}</Text>
        </View>
      </View>

      {/* H5 的目录是锚点跳转；小程序页面内没有 hash 路由，这里作为阅读索引展示。 */}
      <View className='lg-toc'>
        {doc.toc.map((t) => (
          <View className='lg-toc__row' key={t.id}>
            <View className='lg-toc__dot' />
            <Text className='lg-toc__label'>{t.label}</Text>
          </View>
        ))}
      </View>

      <View className='lg-content'>
        {doc.sections.map((s) => (
          <View className='lg-sec' key={s.id}>
            <View className='lg-sec__head'>
              <Text className='lg-sec__index'>{s.index}</Text>
              <Text className='lg-sec__title'>{s.title}</Text>
            </View>
            <View className='lg-sec__rule' />
            <Blocks blocks={s.blocks} />
          </View>
        ))}

        <View className='lg-contact'>联系邮箱：{doc.contactEmail}</View>
      </View>

      <View className='lg-backwrap'>
        <View className='lg-back' onClick={() => Taro.navigateBack()}>
          返回
        </View>
      </View>
    </View>
  )
}
