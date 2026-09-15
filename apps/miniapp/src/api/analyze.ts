import { apiRequest } from './client'
import { storage } from '@/utils/storage'

// 「上次提交的任务」本地记忆：小程序退到后台或被杀掉后再进来，用它在首页给个
// 「报告生成中 / 已生成」的找回入口。30 分钟窗口对齐后端 SSE buffer TTL。
const LAST_TASK_KEY = 'venus.lastTask'
const LAST_TASK_MAX_AGE_MS = 30 * 60 * 1000

export type LastTask = { taskId: string; savedAt: number }

export const LastTaskStore = {
  save(taskId: string) {
    storage.set(LAST_TASK_KEY, { taskId, savedAt: Date.now() })
  },
  get(): LastTask | null {
    const p = storage.get<LastTask>(LAST_TASK_KEY)
    if (!p || !p.taskId || Date.now() - p.savedAt > LAST_TASK_MAX_AGE_MS) {
      this.clear()
      return null
    }
    return p
  },
  clear() {
    storage.remove(LAST_TASK_KEY)
  },
}

export const createAnalyze = (photoId: number) =>
  apiRequest<{ taskId: string; status: string }>('/api/analyze', {
    method: 'POST',
    data: { photoId },
  })

export const getAnalyzeQuota = () =>
  apiRequest<{ blocked: boolean; remaining: number; limit: number }>(
    '/api/analyze/quota',
  )

export interface ReportResp {
  taskId: string
  schemaVersion: string
  stype: Record<string, unknown>
  style: Record<string, unknown>
  subzone: Record<string, unknown>
  struct: Record<string, unknown>
  radarScores: { stype: number; style: number; subzone: number; struct: number }
  radar_semantics?: string | null
  radar_max?: number | null
  state_values?: {
    stype: number
    style: number
    subzone: number
    struct: number
  } | null
  optimization: string
  aesthetic_optimization?: { summary?: string; directions?: string[] } | null
  project_directions?: string[] | null
  mapped_project_directions?: Array<{
    direction?: string
    display_title?: string
    safe_description?: string
    consult_note?: string
  }> | null
  lead_cta?: { title?: string; text?: string; button?: string } | null
  disclaimer?: string | null
  createdAt: string
}

export const getReport = (taskId: string) =>
  apiRequest<ReportResp>(`/api/reports/${taskId}`)
