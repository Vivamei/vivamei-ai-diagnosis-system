import { useEffect, useRef, useState } from "react";
import { AuthStore } from "@/api/client";

export type Phase = "stype" | "style" | "subzone" | "struct";
export type PhaseStatus = "idle" | "streaming" | "done";

export interface PhaseState {
  status: PhaseStatus;
  text: string;
  payload?: Record<string, unknown>;
}

export interface SseState {
  phases: Record<Phase, PhaseState>;
  radar?: { stype: number; style: number; subzone: number; struct: number };
  done: boolean;
  error?: { code: string; retryable: boolean; message?: string; raw?: string };
  // 排队削峰：拿到并发槽前，后端每 ~2s 推 queued 事件。ahead=前面还有几人。
  queueAhead?: number;
}

const emptyPhases = (): SseState["phases"] => ({
  stype: { status: "idle", text: "" },
  style: { status: "idle", text: "" },
  subzone: { status: "idle", text: "" },
  struct: { status: "idle", text: "" },
});

export function useAnalyzeStream(taskId: string | null): SseState {
  const [state, setState] = useState<SseState>(() => ({
    phases: emptyPhases(),
    done: false,
  }));
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!taskId) return;
    // EventSource 无法带 Header，把 accessToken 拼到 query 上（后端有对应回退）
    const t = AuthStore.tokens?.accessToken;
    const url = `/api/analyze/${taskId}/stream${t ? `?token=${encodeURIComponent(t)}` : ""}`;
    const es = new EventSource(url);
    esRef.current = es;

    const json =
      <T,>(handler: (data: T) => void) =>
      (e: MessageEvent) => {
        try {
          handler(JSON.parse(e.data) as T);
        } catch {
          // 帧解析失败忽略
        }
      };

    es.addEventListener(
      "queued",
      json<{ ahead: number }>((d) =>
        setState((s) => ({ ...s, queueAhead: d.ahead })),
      ),
    );
    es.addEventListener(
      "phase",
      json<{ phase: Phase }>((d) =>
        setState((s) => ({
          ...s,
          // 首个 phase 到达 = 已拿到槽开始分析，清掉排队态
          queueAhead: undefined,
          phases: {
            ...s.phases,
            [d.phase]: { ...s.phases[d.phase], status: "streaming" },
          },
        })),
      ),
    );
    es.addEventListener(
      "delta",
      json<{ phase: Phase; text: string }>((d) =>
        setState((s) => ({
          ...s,
          phases: {
            ...s.phases,
            [d.phase]: {
              ...s.phases[d.phase],
              text: s.phases[d.phase].text + (d.text || ""),
            },
          },
        })),
      ),
    );
    es.addEventListener(
      "phase_done",
      json<{ phase: Phase; payload: Record<string, unknown> }>((d) =>
        setState((s) => ({
          ...s,
          phases: {
            ...s.phases,
            [d.phase]: { ...s.phases[d.phase], status: "done", payload: d.payload },
          },
        })),
      ),
    );
    es.addEventListener(
      "radar",
      json<{ radar: SseState["radar"] }>((d) =>
        setState((s) => ({ ...s, radar: d.radar })),
      ),
    );
    es.addEventListener(
      "done",
      json(() => {
        setState((s) => ({ ...s, done: true }));
        es.close();
      }),
    );
    es.addEventListener("error", (e: MessageEvent) => {
      // 连接级错误(网络断/401)不带 data，交给下面的 onerror 处理，这里只管服务端 error 帧
      const raw = e.data as string | undefined;
      if (!raw) return;
      let parsed: { error?: { code: string; retryable: boolean; message?: string } } | undefined;
      try {
        parsed = JSON.parse(raw);
      } catch {
        // 原始错误返回信息即使解析失败也要打到控制台
        console.error("[analyze-stream] 收到无法解析的错误帧", { taskId, raw });
        setState((s) => ({
          ...s,
          error: { code: "STREAM_ERROR", retryable: true, raw },
        }));
        es.close();
        return;
      }
      const err = parsed?.error || { code: "STREAM_ERROR", retryable: true };
      // 错误日志 + 原始错误返回信息打到浏览器控制台
      console.error("[analyze-stream] 分析失败（服务端错误帧）", {
        taskId,
        error: err,
        raw,
      });
      setState((s) => ({
        ...s,
        error: { code: err.code, retryable: err.retryable, message: err.message, raw },
      }));
      es.close();
    });

    // 兜底：连接级失败（401/404/网络断）不会走上面的 named-error（因为没有 data 可 parse）。
    // EventSource 的原生 onerror 在 CONNECTING 状态下会不断重试，只在 CLOSED 时才是真错误。
    es.onerror = () => {
      if (es.readyState !== EventSource.CLOSED) return;
      let firstClose = false;
      setState((s) => {
        if (s.error || s.done) return s;
        firstClose = true;
        return {
          ...s,
          error: { code: "STREAM_DISCONNECTED", retryable: true, message: "连接中断，请重试" },
        };
      });
      if (firstClose) {
        console.error("[analyze-stream] 连接中断（EventSource CLOSED）", { taskId, url });
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [taskId]);

  return state;
}
