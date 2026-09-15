import Taro from '@tarojs/taro'

import { AuthStore } from '@/api/client'

/**
 * 受保护页面的入口守卫。小程序没有 react-router 的 <ProtectedRoute>，
 * 改在页面 useDidShow 里调用：未登录就跳登录页，并把当前页塞进 redirect，
 * 登录成功后跳回来。返回 false 表示已跳走，调用方应停止后续加载。
 */
export function requireLogin(): boolean {
  if (AuthStore.tokens) return true
  const pages = Taro.getCurrentPages()
  const current = pages[pages.length - 1]
  const back = current
    ? `/${current.route}${buildQuery(current.options || {})}`
    : '/pages/home/index'
  Taro.redirectTo({
    url: `/pages/login/index?redirect=${encodeURIComponent(back)}`,
  })
  return false
}

function buildQuery(options: Record<string, string>): string {
  const qs = Object.entries(options)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&')
  return qs ? `?${qs}` : ''
}

export function toast(title: string, icon: 'none' | 'success' | 'error' = 'none') {
  Taro.showToast({ title, icon, duration: 2000 })
}
