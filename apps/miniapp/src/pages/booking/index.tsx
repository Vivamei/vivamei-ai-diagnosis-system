import { useState } from 'react'
import { Button, Input, Picker, Text, View } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'

import { createBooking } from '@/api/booking'
import { BrandHeader } from '@/components/BrandHeader'
import { DisclaimerFooter } from '@/components/DisclaimerFooter'
import { requireLogin } from '@/utils/nav'
import './index.css'

// 与 apps/web/src/pages/Booking.tsx 同一套校验：仅放行 11 位大陆手机号。
const PHONE_RE = /^1[3-9]\d{9}$/

export default function Booking() {
  const [taskId, setTaskId] = useState<string | undefined>(undefined)
  const [source, setSource] = useState<string | undefined>(undefined)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [storeCode, setStoreCode] = useState('')
  // H5 用 <input type="datetime-local"> 一个控件搞定，小程序没有该类型，
  // 拆成日期 + 时间两个 Picker，提交前拼回同样的 `YYYY-MM-DDTHH:mm`。
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  useLoad((opts: Record<string, string>) => {
    if (!requireLogin()) return
    setTaskId(opts.taskId || undefined)
    setSource(opts.source || undefined)
  })

  const formInvalid = !name || !PHONE_RE.test(phone)

  const onSubmit = async () => {
    if (formInvalid || submitting) return
    setErr(null)
    setSubmitting(true)
    try {
      await createBooking({
        name: name.trim(),
        phone,
        storeCode: storeCode.trim() || undefined,
        appointmentAt: date && time ? `${date}T${time}` : undefined,
        taskId,
        source,
      })
      setDone(true)
    } catch (e) {
      setErr(e instanceof Error ? e.message : '提交失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <View className='bk-page'>
        <BrandHeader />
        <View className='bk-done'>
          <View className='bk-done__icon'>✓</View>
          <View className='bk-done__title'>预约提交成功</View>
          <Button className='bk-done__btn' onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}>
            返回首页
          </Button>
        </View>
        <DisclaimerFooter />
      </View>
    )
  }

  return (
    <View className='bk-page'>
      <BrandHeader />

      <View className='bk-title'>预约到店面诊</View>
      <View className='bk-sub'>填写信息后，专业顾问将与你联系确认时间</View>

      <View className='bk-card'>
        <Text className='bk-label'>姓名</Text>
        <Input
          className='bk-input'
          placeholder='请输入您的姓名'
          maxlength={32}
          value={name}
          onInput={(e) => setName(e.detail.value)}
        />

        <Text className='bk-label'>手机号</Text>
        <Input
          className='bk-input'
          type='number'
          placeholder='请输入 11 位手机号'
          maxlength={11}
          value={phone}
          onInput={(e) => setPhone(e.detail.value.replace(/\D/g, ''))}
        />

        <Text className='bk-label'>门店编码（选填）</Text>
        <Input
          className='bk-input'
          placeholder='如有指定门店请填写'
          maxlength={32}
          value={storeCode}
          onInput={(e) => setStoreCode(e.detail.value)}
        />

        <Text className='bk-label'>期望到店时间（选填）</Text>
        <View className='bk-row'>
          <Picker className='bk-row__picker' mode='date' value={date} onChange={(e) => setDate(String(e.detail.value))}>
            <View className={`bk-input bk-picker ${date ? '' : 'bk-picker--empty'}`}>
              {date || '选择日期'}
            </View>
          </Picker>
          <Picker className='bk-row__picker' mode='time' value={time} onChange={(e) => setTime(String(e.detail.value))}>
            <View className={`bk-input bk-picker ${time ? '' : 'bk-picker--empty'}`}>
              {time || '选择时间'}
            </View>
          </Picker>
        </View>

        {err && <View className='bk-err'>{err}</View>}

        <Button
          className={`bk-submit ${formInvalid ? 'bk-submit--off' : ''}`}
          disabled={formInvalid || submitting}
          onClick={onSubmit}
        >
          {submitting ? '提交中…' : '提交预约'}
        </Button>
      </View>

      <DisclaimerFooter />
    </View>
  )
}
