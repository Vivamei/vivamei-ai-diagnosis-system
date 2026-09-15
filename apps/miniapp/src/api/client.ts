import Taro from '@tarojs/taro'

import { config } from '@/config'
import { storage } from '@/utils/storage'

export type Tokens = {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export type StoredUser = {
  id: number
  nickname: string | null
}

const AUTH_MAX_AGE_MS = config.authMaxAgeDays * 24 * 60 * 60 * 1000

// 与 H5 同款策略：登录态带首次登录时间戳（savedAt），超过绝对窗口即失效。
// 刷新 access token 时保留 savedAt，不顺延窗口。
type StoredTokens = Tokens & { savedAt: number }

const TOKEN_KEY = 'venus.auth'
const USER_KEY = 'venus.user'

class _AuthStore {
  get tokens(): Tokens | null {
    const parsed = storage.get<StoredTokens>(TOKEN_KEY)
    if (!parsed) return null
    if (
      typeof parsed.savedAt === 'number' &&
      Date.now() - parsed.savedAt > AUTH_MAX_AGE_MS
    ) {
      this.clear()
      return null
    }
    return parsed
  }

  setTokens(t: Tokens) {
    storage.set(TOKEN_KEY, { ...t, savedAt: Date.now() } as StoredTokens)
  }

  updateAccessToken(accessToken: string, expiresIn: number) {
    const prev = storage.get<StoredTokens>(TOKEN_KEY)
    if (!prev) return
    storage.set(TOKEN_KEY, { ...prev, accessToken, expiresIn })
  }

  get user(): StoredUser | null {
    return storage.get<StoredUser>(USER_KEY)
  }

  setUser(u: StoredUser) {
    storage.set(USER_KEY, u)
  }

  clear() {
    storage.remove(TOKEN_KEY)
    storage.remove(USER_KEY)
  }
}

export const AuthStore = new _AuthStore()

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public requestId?: string,
  ) {
    super(message)
  }
}

function requestFailureMessage(reason: unknown): string {
  const raw =
    reason instanceof Error
      ? reason.message
      : typeof reason === 'object' && reason !== null && 'errMsg' in reason
        ? String((reason as { errMsg?: unknown }).errMsg || '')
        : ''
  const normalized = raw.toLowerCase()

  if (normalized.includes('url not in domain list')) {
    return '服务器域名配置异常，请联系管理员'
  }
  if (normalized.includes('timeout')) {
    return '连接服务器超时，请检查网络后重试'
  }
  if (
    normalized.includes('ssl') ||
    normalized.includes('certificate') ||
    normalized.includes('handshake')
  ) {
    return '服务器 HTTPS 连接失败，请联系管理员'
  }
  return raw ? `无法连接服务器：${raw}` : '无法连接服务器，请检查网络后重试'
}

async function taroRequest(options: Taro.request.Option) {
  try {
    return await Taro.request(options)
  } catch (reason) {
    throw new ApiError('NETWORK_ERROR', requestFailureMessage(reason), 0)
  }
}

let refreshing: Promise<Tokens> | null = null

async function doRefresh(): Promise<Tokens> {
  const t = AuthStore.tokens
  if (!t) throw new ApiError('AUTH_REQUIRED', 'not logged in', 401)
  const res = await taroRequest({
    url: `${config.apiBase}/api/auth/refresh`,
    method: 'POST',
    header: { 'content-type': 'application/json' },
    data: { refreshToken: t.refreshToken },
  })
  if (res.statusCode < 200 || res.statusCode >= 300) {
    AuthStore.clear()
    throw new ApiError('AUTH_REFRESH_FAILED', 'refresh failed', res.statusCode)
  }
  const data = res.data as { accessToken: string; expiresIn: number }
  AuthStore.updateAccessToken(data.accessToken, data.expiresIn)
  return { ...t, accessToken: data.accessToken, expiresIn: data.expiresIn }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  header?: Record<string, string>
  /** true 时不带 Authorization、401 也不刷新（登录类接口用）。 */
  anonymous?: boolean
}

export async function apiRequest<T = unknown>(
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', data, header = {}, anonymous = false } = opts
  const t = anonymous ? null : AuthStore.tokens

  const send = (accessToken?: string) =>
    taroRequest({
      url: `${config.apiBase}${path}`,
      method,
      data: data as Taro.request.Option['data'],
      header: {
        'content-type': 'application/json',
        ...header,
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    })

  let res = await send(t?.accessToken)

  // 401 时静默刷新一次再重放。多个并发请求共用同一个刷新 Promise，避免打爆 /refresh。
  if (res.statusCode === 401 && t) {
    refreshing =
      refreshing ||
      doRefresh().finally(() => {
        refreshing = null
      })
    const fresh = await refreshing
    res = await send(fresh.accessToken)
  }

  if (res.statusCode < 200 || res.statusCode >= 300) {
    const body = (res.data || {}) as Record<string, unknown>
    throw new ApiError(
      (body.code as string) || 'HTTP_ERROR',
      (body.message as string) || `HTTP ${res.statusCode}`,
      res.statusCode,
      body.requestId as string | undefined,
    )
  }
  return res.data as T
}
