import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAnalyzeStream, Phase } from "@/hooks/useSse";
import { PhaseProgress } from "@/components/PhaseProgress";
import { StreamingText } from "@/components/StreamingText";
import { BrandHeader } from "@/components/BrandHeader";

const labels: Record<Phase, string> = {
  style: "分型 Style",
  stype: "分相 Stype",
  subzone: "分区 Subzone",
  struct: "分层 Struct",
};

// 分析页文案/时长的兜底默认值。真实值由后端 /api/config 提供（可在外置 .env 调整）。
const FALLBACK_CFG = {
  analyzeEtaSeconds: 150,
  analyzeTitlePreparing: "AI 分析准备中…",
  analyzeTitleAnalyzing: "AI 正在为您分析…",
  analyzeSubtitle: "分型 · 分相 · 分区 · 分层",
  analyzeWaitHints: [
    "正在读取面部轮廓与光影结构…",
    "比对分型 / 分相 / 分区 / 分层四维模型…",
    "结合个人特征生成美学建议…",
    "即将完成，正在整理报告…",
  ],
  analyzeWaitNote: "请勿关闭页面",
};
type AnalyzeCfg = typeof FALLBACK_CFG;

// 把预计秒数格式化成友好文案：>=90s 用「分钟」，否则用「秒」。
function fmtEta(sec: number): string {
  if (sec >= 90) {
    const lo = Math.floor(sec / 60);
    const hi = Math.ceil(sec / 60);
    return `预计 ${lo === hi ? lo : `${lo}–${hi}`} 分钟`;
  }
  return `预计 ${sec} 秒`;
}

export default function Analyzing() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const sse = useAnalyzeStream(id || null);

  // 拉取后端公开配置（文案 + 预计时长）；失败则用兜底默认值，不影响主流程。
  const [cfg, setCfg] = useState<AnalyzeCfg>(FALLBACK_CFG);
  useEffect(() => {
    let alive = true;
    fetch("/api/config")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!alive || !d) return;
        setCfg({
          analyzeEtaSeconds: d.analyzeEtaSeconds ?? FALLBACK_CFG.analyzeEtaSeconds,
          analyzeTitlePreparing:
            d.analyzeTitlePreparing || FALLBACK_CFG.analyzeTitlePreparing,
          analyzeTitleAnalyzing:
            d.analyzeTitleAnalyzing || FALLBACK_CFG.analyzeTitleAnalyzing,
          analyzeSubtitle: d.analyzeSubtitle || FALLBACK_CFG.analyzeSubtitle,
          analyzeWaitHints:
            Array.isArray(d.analyzeWaitHints) && d.analyzeWaitHints.length
              ? d.analyzeWaitHints
              : FALLBACK_CFG.analyzeWaitHints,
          analyzeWaitNote: d.analyzeWaitNote || FALLBACK_CFG.analyzeWaitNote,
        });
      })
      .catch(() => {
        // 配置拉取失败忽略，用兜底默认值
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (sse.done && id) nav(`/report/${id}`);
  }, [sse.done, id, nav]);

  const anyActive =
    sse.phases.stype.status !== "idle" ||
    sse.phases.style.status !== "idle" ||
    sse.phases.subzone.status !== "idle" ||
    sse.phases.struct.status !== "idle";

  // 等待期计时：首个 phase 事件到达前每秒 +1，进入分析/出错后停止
  const [elapsed, setElapsed] = useState(0);
  const waiting = !anyActive && !sse.done && !sse.error;
  useEffect(() => {
    if (!waiting) return;
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [waiting]);

  // 渐进提示 + 渐近进度（永远到不了 100，真数据到达才收尾）。
  // 提示与进度曲线都按预计时长自适应：滚动提示均摊到整个等待期，
  // 进度曲线的时间常数取 eta/2.3，使 elapsed≈eta 时逼近约 90%。
  const eta = cfg.analyzeEtaSeconds;
  const hints = cfg.analyzeWaitHints;
  const hintStep = Math.max(1, eta / hints.length);
  const hint = hints[Math.min(Math.floor(elapsed / hintStep), hints.length - 1)];
  const tau = Math.max(1, eta / 2.3);
  const pct = Math.min(96, Math.round((1 - Math.exp(-elapsed / tau)) * 100));

  // 排队态：后端还没给这个任务分到并发槽，展示位次而非渐进进度条。
  const queued = waiting && sse.queueAhead != null;
  const queueAhead = sse.queueAhead ?? 0;


  // 接口失败：停止 loading，直接给错误提示。
  // 原始错误返回信息已在 useSse 里打进浏览器控制台（后端也会写 log 文件）。
  if (sse.error) {
    return (
      <div style={{ padding: 16, paddingBottom: 32 }}>
        <BrandHeader />
        <div
          style={{
            marginTop: 24,
            background: "#1c1815",
            borderRadius: 20,
            padding: 24,
            border: "1px solid rgba(214,110,90,0.4)",
            boxShadow: "0 12px 32px rgba(28,24,21,0.24)",
            textAlign: "center",
          }}
        >
          <h2 style={{ fontSize: 17, color: "var(--danger)", margin: "0 0 10px" }}>
            分析失败
          </h2>
          <p style={{ fontSize: 13, color: "#e6dcc9", margin: "0 0 6px" }}>
            {sse.error.message || "分析过程中出现问题，请稍后重试。"}
          </p>
          <div
            style={{
              fontSize: 11,
              color: "var(--ink-soft)",
              marginBottom: 18,
              wordBreak: "break-all",
            }}
          >
            错误码：{sse.error.code}
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            {sse.error.retryable && (
              <button
                onClick={() => window.location.reload()}
                style={{
                  background: "linear-gradient(135deg,var(--gold),var(--gold-deep))",
                  border: "none",
                  color: "#1c1815",
                  padding: "8px 20px",
                  borderRadius: 14,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                重试
              </button>
            )}
            <button
              onClick={() => nav("/")}
              style={{
                background: "none",
                border: "1px solid rgba(200,163,118,0.4)",
                color: "#c8a376",
                padding: "8px 20px",
                borderRadius: 14,
                cursor: "pointer",
              }}
            >
              返回首页
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, paddingBottom: 32 }}>
      <BrandHeader />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
          margin: "12px 0 6px",
        }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: "50%",
            border: "2.5px solid rgba(200,163,118,0.25)",
            borderTopColor: "#c8a376",
            animation: "spin 0.9s linear infinite",
          }}
        />
        <h2 style={{ fontSize: 17, color: "var(--ink)", margin: 0 }}>
          {anyActive ? cfg.analyzeTitleAnalyzing : cfg.analyzeTitlePreparing}
        </h2>
      </div>
      <div
        style={{
          textAlign: "center",
          fontSize: 11,
          color: "var(--ink-soft)",
          letterSpacing: 2,
          marginBottom: 16,
        }}
      >
        {cfg.analyzeSubtitle}
      </div>

      {/* 等待期兜底：首个 phase 事件到达前展示预计等待 + 渐进进度 */}
      {waiting && (
        <div
          style={{
            background: "#1c1815",
            borderRadius: 20,
            padding: 18,
            marginBottom: 16,
            border: "1px solid rgba(200,163,118,0.18)",
            boxShadow: "0 12px 32px rgba(28,24,21,0.24)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 10,
            }}
          >
            <div style={{ fontSize: 13, color: "#e6dcc9" }}>
              {queued
                ? queueAhead > 0
                  ? `排队中，前面还有 ${queueAhead} 人`
                  : "即将开始，正在为您准备…"
                : hint}
            </div>
            <div style={{ fontSize: 12, color: "#c8a376", fontWeight: 700 }}>
              {queued ? (queueAhead > 0 ? `第 ${queueAhead + 1} 位` : "即将开始") : `${pct}%`}
            </div>
          </div>
          {!queued && (
            <div
              style={{
                height: 8,
                borderRadius: 6,
                background: "rgba(240,230,213,0.1)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  borderRadius: 6,
                  background:
                    "linear-gradient(135deg,var(--gold),var(--gold-deep))",
                  transition: "width 0.9s ease",
                }}
              />
            </div>
          )}
          <div
            style={{
              marginTop: 10,
              fontSize: 11,
              color: "var(--ink-soft)",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <span>已等待 {elapsed}s</span>
            <span>
              {queued
                ? `活动高峰期，正在排队处理，${cfg.analyzeWaitNote}`
                : `${fmtEta(eta)}，${cfg.analyzeWaitNote}`}
            </span>
          </div>
        </div>
      )}

      <PhaseProgress states={sse.phases} />

      <div
        style={{
          marginTop: 16,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {(Object.keys(labels) as Phase[]).map((p) => {
          const st = sse.phases[p];
          const isStreaming = st.status === "streaming";
          const isDone = st.status === "done";
          const isIdle = st.status === "idle";
          return (
            <div
              key={p}
              style={{
                background: "#1c1815",
                padding: 16,
                borderRadius: 20,
                boxShadow: isStreaming
                  ? "0 0 0 1px rgba(200,163,118,0.5), 0 14px 36px rgba(200,163,118,0.25)"
                  : "0 12px 32px rgba(28, 24, 21, 0.24)",
                border: "1px solid rgba(200, 163, 118, 0.18)",
                color: "#e6dcc9",
                opacity: isIdle ? 0.55 : 1,
                transform: isStreaming ? "scale(1.01)" : "scale(1)",
                transition:
                  "opacity 0.4s ease, transform 0.35s ease, box-shadow 0.35s ease",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    fontSize: 13,
                    color: "#c8a376",
                    fontWeight: 700,
                    letterSpacing: 0.5,
                  }}
                >
                  {labels[p]}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: isDone
                      ? "#88b09a"
                      : isStreaming
                        ? "#c8a376"
                        : "rgba(240,230,213,0.4)",
                    fontWeight: 500,
                  }}
                >
                  {isDone ? "✓ 完成" : isStreaming ? "生成中…" : "等待中"}
                </div>
              </div>
              {isIdle ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  <div className="skeleton-line" style={{ width: "92%" }} />
                  <div className="skeleton-line" style={{ width: "78%" }} />
                  <div className="skeleton-line" style={{ width: "64%" }} />
                </div>
              ) : (
                <StreamingText text={st.text} active={isStreaming} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
