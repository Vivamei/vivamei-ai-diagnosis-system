import Taro from '@tarojs/taro'

import { config } from '@/config'
import { apiRequest, ApiError, AuthStore } from './client'

export interface StsResp {
  ossEndpoint: string
  accessKeyId: string
  accessKeySecret: string
  securityToken: string
  expiration: string
  objectKey: string
  maxBytes: number
}

export const getUploadToken = () =>
  apiRequest<StsResp>('/api/upload/token', { method: 'POST', data: {} })

/**
 * 本地/后端代传：小程序拿到的是临时文件路径而不是 Blob，multipart 只能交给
 * Taro.uploadFile 拼（它不走 Taro.request，所以 401 静默刷新在这里不生效——
 * 调用方应在上传前已完成登录，失败按 401 引导重登）。
 */
export async function uploadLocal(objectKey: string, filePath: string): Promise<void> {
  const t = AuthStore.tokens
  const res = await Taro.uploadFile({
    url: `${config.apiBase}/api/upload/local`,
    filePath,
    name: 'file',
    formData: { objectKey },
    header: t ? { Authorization: `Bearer ${t.accessToken}` } : {},
  })
  if (res.statusCode < 200 || res.statusCode >= 300) {
    let body: Record<string, unknown> = {}
    try {
      body = JSON.parse(res.data)
    } catch {
      // uploadFile 的 data 是字符串，解析失败也要抛错
    }
    throw new ApiError(
      (body.code as string) || 'UPLOAD_LOCAL_FAILED',
      (body.message as string) || `HTTP ${res.statusCode}`,
      res.statusCode,
      body.requestId as string | undefined,
    )
  }
}

export interface PhotoMeta {
  ossKey: string
  width?: number
  height?: number
  bytes?: number
  mime?: string
}

export const registerPhoto = (p: PhotoMeta) =>
  apiRequest<{ photoId: number; moderationStatus: string }>('/api/photos', {
    method: 'POST',
    data: p,
  })
