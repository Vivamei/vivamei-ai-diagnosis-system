import Taro from '@tarojs/taro'

import { config } from '@/config'
import { apiRequest, AuthStore, Tokens } from './client'

export interface VerifyResp extends Tokens {
  user: { id: number; nickname: string | null }
}

function persist(data: VerifyResp): VerifyResp {
  AuthStore.setTokens(data)
  AuthStore.setUser(data.user)
  return data
}

export const smsSend = (phone: string) =>
  apiRequest<{ expiresIn: number }>('/api/auth/sms/send', {
    method: 'POST',
    data: { phone, scene: 'login' },
    anonymous: true,
  })

export async function smsVerify(phone: string, code: string): Promise<VerifyResp> {
  const data = await apiRequest<VerifyResp>('/api/auth/sms/verify', {
    method: 'POST',
    data: { phone, code, consentVer: config.consentVer },
    anonymous: true,
  })
  return persist(data)
}

export interface WxLoginResp {
  needPhone: boolean
  bindToken?: string | null
  tokens?: VerifyResp | null
}

/** 静默登录：拿 wx.login 的 code 去换 openid。已绑过手机号则直接返回 tokens。 */
export async function wxLogin(): Promise<WxLoginResp> {
  const { code } = await Taro.login()
  const data = await apiRequest<WxLoginResp>('/api/auth/wx/login', {
    method: 'POST',
    data: { code },
    anonymous: true,
  })
  if (!data.needPhone && data.tokens) persist(data.tokens)
  return data
}

/** 手机号授权回调：把 <Button open-type="getPhoneNumber"> 给的 code 连同 bindToken 换正式登录态。 */
export async function wxBindPhone(
  bindToken: string,
  phoneCode: string,
): Promise<VerifyResp> {
  const data = await apiRequest<VerifyResp>('/api/auth/wx/phone', {
    method: 'POST',
    data: { bindToken, phoneCode, consentVer: config.consentVer },
    anonymous: true,
  })
  return persist(data)
}
