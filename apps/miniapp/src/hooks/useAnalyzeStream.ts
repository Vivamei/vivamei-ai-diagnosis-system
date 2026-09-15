import { useEffect, useRef, useState } from 'react'
import Taro from '@tarojs/taro'

import { AuthStore } from '@/api/client'
import { config } from '@/config'
import { SseParser, Utf8ChunkDecoder } from '@/utils/sse'

export type Phase = 'stype' | 'style' | 'subzone' | 'struct'
export type PhaseStatus = 'idle' | 'streaming' | 'done'

export interface PhaseState {
  status: PhaseStatus
  text: string
  payload?: Record<string, unknown>
}

export interface StreamState {
  phases: Record<Phase, PhaseState>
  radar?: { stype: number; style: number; subzone: number; struct: number }
  done: boolean
  error?: { code: string; retryable: boolean; message?: string }
  /** 排队削峰：拿到并发槽前后端每 ~2s 推 queued 事件，ahead=前面还有几人。 */
  queueAhead?: number
}

const emptyPhases = (): StreamState['phases'] => ({
  stype: { status: 'idle', text: '' },
  style: { status: 'idle', text: '' },
  subzone: { status: 'idle', text: '' },
  struct: { status: 'idle', text: '' },
})

const MAX_RETRIES = 5
// 微信请求通常受 60s 网络超时约束。主动在 45s 轮换连接，再用 Last-Event-ID
// 从最后一帧之后续传；后端 Redis Stream 保留 30 分钟，不会丢事件或重复拼 delta。
const ROTATE_MS = 45_000
const REQUEST_TIMEOUT_MS = 55_000

/**
 * 分析进度订阅。H5 使用 EventSource；小程序没有原生 EventSource，因此通过
 * Taro.request(enableChunked) 读取同一条 SSE 接口。连接按 45s 主动轮换，并通过
 * Last-Event-ID 从 Redis Stream 续传，事件语义与 H5 完全一致。
 */
export function useAnalyzeStream(taskId: string | null): StreamState {
  const [state, setState] = useState<StreamState>(() => ({
    phases: emptyPhases(),
    done: false,
  }))
  const lastIdRef = useRef<string | null>(null)
  const retriesRef = useRef(0)
  const closedRef = useRef(false)
  const taskRef = useRef<Taro.RequestTask<ArrayBuffer> | null>(null)

  useEffect(() => {
    if (!taskId) return
    closedRef.current = false
    lastIdRef.current = null
    retriesRef.current = 0

    const handle = (event: string, data: string) => {
      let d: any
      try {
        d = JSON.parse(data)
      } catch {
        d = {}
      }
      switch (event) {
        case 'queued':
          setState((s) => ({ ...s, queueAhead: d.ahead }))
          break
        case 'phase':
          setState((s) => ({
            ...s,
            // 首个 phase 到达 = 已拿到并发槽，清掉排队态
            queueAhead: undefined,
            phases: {
              ...s.phases,
              [d.phase]: { ...s.phases[d.phase], status: 'streaming' },
            },
          }))
          break
        case 'delta':
          setState((s) => ({
            ...s,
            phases: {
              ...s.phases,
              [d.phase]: {
                ...s.phases[d.phase],
                text: s.phases[d.phase].text + (d.text || ''),
              },
            },
          }))
          break
        case 'phase_done':
          setState((s) => ({
            ...s,
            phases: {
              ...s.phases,
              [d.phase]: {
                ...s.phases[d.phase],
                status: 'done',
                payload: d.payload,
              },
            },
          }))
          break
        case 'radar':
          setState((s) => ({ ...s, radar: d.radar }))
          break
        case 'done':
          closedRef.current = true
          setState((s) => ({ ...s, done: true }))
          break
        case 'error': {
          closedRef.current = true
          const err = d.error || { code: d.code || 'STREAM_ERROR', retryable: true }
          console.error('[analyze-stream] 分析失败', { taskId, err })
          setState((s) => ({
            ...s,
            error: {
              code: err.code,
              retryable: !!err.retryable,
              message: err.message || d.message,
            },
          }))
          break
        }
        default:
          break
      }
    }

    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let rotateTimer: ReturnType<typeof setTimeout> | null = null

    const stop = () => {
      closedRef.current = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (rotateTimer) clearTimeout(rotateTimer)
      taskRef.current?.abort()
      taskRef.current = null
    }

    const failConnection = (message = '连接中断，请重试') => {
      if (closedRef.current) return
      if (retriesRef.current >= MAX_RETRIES) {
        stop()
        setState((s) =>
          s.error || s.done
            ? s
            : {
                ...s,
                error: {
                  code: 'STREAM_DISCONNECTED',
                  retryable: true,
                  message,
                },
              },
        )
        return
      }
      const delay = 500 * 2 ** retriesRef.current
      retriesRef.current += 1
      reconnectTimer = setTimeout(connect, delay)
    }

    const connect = () => {
      if (closedRef.current) return
      const token = AuthStore.tokens?.accessToken || ''
      const decoder = new Utf8ChunkDecoder()
      const parser = new SseParser((frame) => {
        if (frame.id) lastIdRef.current = frame.id
        retriesRef.current = 0
        handle(frame.event, frame.data)
      })

      let rotating = false
      let sawChunk = false
      const task = Taro.request<ArrayBuffer>({
        url: `${config.apiBase}/api/analyze/${taskId}/stream`,
        method: 'GET',
        header: {
          Accept: 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(lastIdRef.current ? { 'Last-Event-ID': lastIdRef.current } : {}),
        },
        enableChunked: true,
        responseType: 'arraybuffer',
        timeout: REQUEST_TIMEOUT_MS,
      })
      taskRef.current = task

      if (typeof task.onChunkReceived === 'function') {
        task.onChunkReceived(({ data }) => {
          if (closedRef.current) return
          sawChunk = true
          retriesRef.current = 0
          parser.push(decoder.decode(data))
        })
      }

      // 主动轮换不算失败；新请求携带 Last-Event-ID，无缝接着读取。
      rotateTimer = setTimeout(() => {
        if (closedRef.current || taskRef.current !== task) return
        rotating = true
        task.abort()
      }, ROTATE_MS)

      task.then(
        (res) => {
          if (rotateTimer) clearTimeout(rotateTimer)
          if (taskRef.current === task) taskRef.current = null
          if (closedRef.current) return

          if (res.statusCode < 200 || res.statusCode >= 300) {
            let body: { code?: string; message?: string } = {}
            try {
              const text = new Utf8ChunkDecoder().decode(res.data, true)
              body = JSON.parse(text)
            } catch {
              // 非 JSON 错误响应按 HTTP 状态展示
            }
            stop()
            setState((s) => ({
              ...s,
              error: {
                code: body.code || `STREAM_HTTP_${res.statusCode}`,
                retryable: res.statusCode >= 500,
                message: body.message || `进度接口返回 HTTP ${res.statusCode}`,
              },
            }))
            return
          }

          // 不支持 onChunkReceived 的兼容环境会在请求结束后一次性拿到完整 SSE。
          if (!sawChunk && res.data) parser.push(decoder.decode(res.data))
          parser.push(decoder.finish())
          parser.finish()
          if (!closedRef.current) failConnection()
        },
        (err) => {
          if (rotateTimer) clearTimeout(rotateTimer)
          if (taskRef.current === task) taskRef.current = null
          if (closedRef.current) return
          if (rotating) {
            reconnectTimer = setTimeout(connect, 50)
            return
          }
          const msg = String((err as { errMsg?: string })?.errMsg || '')
          failConnection(msg.includes('timeout') ? '进度连接超时，正在重试' : undefined)
        },
      )
    }

    connect()

    return () => {
      stop()
    }
  }, [taskId])

  return state
}
