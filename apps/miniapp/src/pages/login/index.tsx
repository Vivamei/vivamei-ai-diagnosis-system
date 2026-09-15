import { useRef, useState } from 'react'
import { Button, Checkbox, Input, Text, View } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'

import { smsSend, smsVerify, wxBindPhone, wxLogin } from '@/api/auth'
import { AuthStore } from '@/api/client'
import { COPY } from '@/config'
import { useCountdown } from '@/hooks/useCountdown'
import './index.css'

const PHONE_RE = /^1[3-9]\d{9}$/

// H5 没有小程序登录及手机号快速验证能力，只能走短信验证码。
const IS_WEAPP = process.env.TARO_ENV === 'weapp'

export default function Login() {
  const [redirect, setRedirect] = useState('/pages/home/index')
  const [bindToken, setBindToken] = useState<string | null>(null)
  const [smsMode, setSmsMode] = useState(!IS_WEAPP)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [consent, setConsent] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const wxLoginInFlight = useRef<ReturnType<typeof wxLogin> | null>(null)
  const cd = useCountdown()

  const done = () => Taro.redirectTo({ url: redirect })

  // 页面初始化和用户点击可能同时发生，共用同一次静默登录，避免一次性 code 被并发消费。
  const prepareWxLogin = () => {
    if (!wxLoginInFlight.current) {
      wxLoginInFlight.current = wxLogin().finally(() => {
        wxLoginInFlight.current = null
      })
    }
    return wxLoginInFlight.current
  }

  useLoad((opts: Record<string, string>) => {
    if (opts.redirect) setRedirect(decodeURIComponent(opts.redirect))
    if (AuthStore.tokens) {
      done()
      return
    }
    if (!IS_WEAPP) return
    // 静默登录：openid 之前绑过手机号就直接进去，用户无感。
    prepareWxLogin()
      .then((r) => {
        if (!r.needPhone) done()
        else setBindToken(r.bindToken || null)
      })
      .catch((e) => {
        // 快捷登录不可用时不打断，用户仍可切换到验证码登录。
        setErr(e instanceof Error ? e.message : '快捷登录初始化失败')
        setSmsMode(true)
      })
  })

  const requireConsent = () => {
    if (consent) return true
    setErr('请先勾选同意《隐私政策》与《用户协议》')
    return false
  }

  const onGetPhone = async (e: any) => {
    setErr(null)
    if (!requireConsent()) return
    const detail = e.detail || {}
    if (!detail.code) {
      const message = String(detail.errMsg || '')
      setErr(
        message.includes('deny')
          ? '已取消手机号授权'
          : '未取得手机号授权，请重试或使用验证码登录',
      )
      return
    }
    setSubmitting(true)
    try {
      let token = bindToken
      if (!token) {
        // 初始化曾失败或用户点得较快时，在这里重新取得绑定令牌。
        const login = await prepareWxLogin()
        if (!login.needPhone) {
          done()
          return
        }
        token = login.bindToken || null
        setBindToken(token)
      }
      if (!token) throw new Error('快捷登录初始化失败，请重试')
      await wxBindPhone(token, detail.code)
      done()
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : '登录失败')
    } finally {
      setSubmitting(false)
    }
  }

  const onSend = async () => {
    setErr(null)
    if (!requireConsent()) return
    if (!PHONE_RE.test(phone)) {
      setErr('请输入正确的手机号')
      return
    }
    try {
      await smsSend(phone)
      cd.start(60)
    } catch (e) {
      setErr(e instanceof Error ? e.message : '发送失败')
    }
  }

  const canSubmit =
    PHONE_RE.test(phone) &&
    /^\d{6}$/.test(code) &&
    consent &&
    !submitting

  const onSubmit = async () => {
    setErr(null)
    if (!requireConsent()) return
    setSubmitting(true)
    try {
      await smsVerify(phone, code)
      done()
    } catch (e) {
      setErr(e instanceof Error ? e.message : '登录失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View className='login-page'>
      <View className='login-hero'>
        <View className='login-hero__name'>{COPY.brandName}</View>
        <View className='login-hero__sub'>{COPY.brandSubtitle}</View>
        <View className='login-hero__tip'>登录后开始薇分美学4S体验</View>
      </View>

      <View className='login-card'>
        {smsMode && (
          <View>
            <Text className='login-label'>手机号</Text>
            <Input
              className='login-input'
              type='number'
              placeholder='请输入 11 位手机号'
              maxlength={11}
              value={phone}
              onInput={(e) => setPhone(e.detail.value.replace(/\D/g, ''))}
            />

            <Text className='login-label'>验证码</Text>
            <View className='login-row'>
              <Input
                className='login-input'
                type='number'
                placeholder='6 位验证码'
                maxlength={6}
                value={code}
                onInput={(e) => setCode(e.detail.value.replace(/\D/g, ''))}
              />
              <Button
                className={`login-sendbtn ${cd.remaining > 0 ? 'is-disabled' : ''}`}
                disabled={cd.remaining > 0}
                onClick={onSend}
              >
                {cd.remaining > 0 ? `${cd.remaining}s` : '获取验证码'}
              </Button>
            </View>
          </View>
        )}

        <View className='login-consent'>
          <Checkbox
            className='login-consent__box'
            value='consent'
            checked={consent}
            color='#c8a376'
            onClick={() => setConsent((v) => !v)}
          />
          <Text onClick={() => setConsent((v) => !v)}>
            我已阅读并同意
            <Text
              className='login-link'
              onClick={(e) => {
                // 点链接不应顺带切换勾选状态，小程序端需手动阻断冒泡。
                e.stopPropagation()
                Taro.navigateTo({ url: '/pages/legal/privacy/index' })
              }}
            >
              《隐私政策》
            </Text>
            与
            <Text
              className='login-link'
              onClick={(e) => {
                e.stopPropagation()
                Taro.navigateTo({ url: '/pages/legal/terms/index' })
              }}
            >
              《用户协议》
            </Text>
          </Text>
        </View>

        {smsMode ? (
          <Button className='login-submit' disabled={!canSubmit} onClick={onSubmit}>
            {submitting ? '登录中…' : '登录'}
          </Button>
        ) : (
          <Button
            className='login-phone'
            openType='getPhoneNumber'
            disabled={!consent || submitting}
            onGetPhoneNumber={onGetPhone}
          >
            {submitting ? '登录中…' : '手机号快捷登录'}
          </Button>
        )}

        {IS_WEAPP && (
          <View className='login-switch' onClick={() => { setErr(null); setSmsMode((v) => !v) }}>
            {smsMode ? '返回手机号快捷登录' : '使用验证码登录'}
          </View>
        )}

        <View
          className='login-skip'
          onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}
        >
          暂不登录，先浏览首页
        </View>

        {err && <View className='login-err'>{err}</View>}
      </View>

      <View className='login-foot'>
        <View className='disclaimer'>{COPY.disclaimerLine1}</View>
        <View className='disclaimer'>{COPY.disclaimerLine2}</View>
      </View>
    </View>
  )
}
