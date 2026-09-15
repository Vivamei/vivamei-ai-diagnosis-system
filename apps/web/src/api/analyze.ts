import { apiFetch } from "./client";

// 「上次提交的任务」本地记忆：提交成功即写入，用于用户中途离开 App 后再进来时，
// 在首页给个「报告生成中 / 已生成，点此查看」的入口找回任务。taskId 平时只活在 URL
// 里（/analyzing/:id、/report/:id），微信里关掉重开 URL 就丢了，故单独持久化一份。
// 30 分钟窗口对齐后端 SSE buffer TTL：过期后视为过时不再提示，避免几天后还弹旧任务。
const LAST_TASK_KEY = "venus.lastTask";
const LAST_TASK_MAX_AGE_MS = 30 * 60 * 1000;

export type LastTask = { taskId: string; savedAt: number };

export const LastTaskStore = {
  save(taskId: string) {
    localStorage.setItem(
      LAST_TASK_KEY,
      JSON.stringify({ taskId, savedAt: Date.now() }),
    );
  },
  get(): LastTask | null {
    const raw = localStorage.getItem(LAST_TASK_KEY);
    if (!raw) return null;
    try {
      const p = JSON.parse(raw) as LastTask;
      if (!p.taskId || Date.now() - p.savedAt > LAST_TASK_MAX_AGE_MS) {
        this.clear();
        return null;
      }
      return p;
    } catch {
      this.clear();
      return null;
    }
  },
  clear() {
    localStorage.removeItem(LAST_TASK_KEY);
  },
};

export const createAnalyze = (photoId: number) =>
  apiFetch<{ taskId: string; status: string }>("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ photoId }),
  });

// 只读查询今日剩余生成次数，用于「开始测一测」前置拦截（不消耗配额）。
export const getAnalyzeQuota = () =>
  apiFetch<{ blocked: boolean; remaining: number; limit: number }>(
    "/api/analyze/quota",
  );

export const getReport = (taskId: string) =>
  apiFetch<{
    taskId: string;
    schemaVersion: string;
    stype: Record<string, unknown>;
    style: Record<string, unknown>;
    subzone: Record<string, unknown>;
    struct: Record<string, unknown>;
    radarScores: { stype: number; style: number; subzone: number; struct: number };
    radar_semantics?: string | null;
    radar_max?: number | null;
    state_values?: {
      stype: number;
      style: number;
      subzone: number;
      struct: number;
    } | null;
    optimization: string;
    aesthetic_optimization?: { summary?: string; directions?: string[] } | null;
    project_directions?: string[] | null;
    mapped_project_directions?: Array<{
      direction?: string;
      display_title?: string;
      safe_description?: string;
      consult_note?: string;
    }> | null;
    lead_cta?: { title?: string; text?: string; button?: string } | null;
    disclaimer?: string | null;
    image_quality?: unknown;
    createdAt: string;
  }>(`/api/reports/${taskId}`);
