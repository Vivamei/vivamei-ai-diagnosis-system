import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { COPY } from "@/config/copy";
import { getAnalyzeQuota, getReport, LastTaskStore } from "@/api/analyze";
import { ApiError } from "@/api/client";

const fourS = [
  { k: "分相", e: "Stype", d: "骨/肉/皮相主导" },
  { k: "分型", e: "Style", d: "气质风格分型" },
  { k: "分区", e: "Subzone", d: "美学分区评估" },
  { k: "分层", e: "Struct", d: "结构层次评估" },
];

export default function Home() {
  const nav = useNavigate();
  const [checking, setChecking] = useState(false);
  const [blockMsg, setBlockMsg] = useState<string | null>(null);

  // 续看入口：用户上次提交过任务且还在 30 分钟窗口内，进首页时查一下它的状态——
  // 已生成则给「查看报告」入口（跳 /report），还在生成则给「继续查看」入口（跳 /analyzing）。
  // 任务不存在（404）说明已过期/被清，直接抹掉本地记忆；网络等其它错误忽略，不显示入口。
  const [resume, setResume] = useState<{ taskId: string; ready: boolean } | null>(
    null,
  );
  useEffect(() => {
    const last = LastTaskStore.get();
    if (!last) return;
    let alive = true;
    getReport(last.taskId)
      .then(() => {
        if (alive) setResume({ taskId: last.taskId, ready: true });
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 425) {
          setResume({ taskId: last.taskId, ready: false });
        } else if (e instanceof ApiError && e.status === 404) {
          LastTaskStore.clear();
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  const goResume = () => {
    if (!resume) return;
    nav(resume.ready ? `/report/${resume.taskId}` : `/analyzing/${resume.taskId}`);
  };

  // 点击「开始测一测」先查今日配额，超限则原地提示、不进拍照页；
  // 查询失败则放行（真正的限流仍由生成接口兜底），不因偶发抖动挡住用户。
  const handleStart = async () => {
    if (checking) return;
    setChecking(true);
    setBlockMsg(null);
    try {
      const q = await getAnalyzeQuota();
      if (q.blocked) {
        setBlockMsg(COPY.quotaExhausted);
        return;
      }
      nav("/capture");
    } catch {
      nav("/capture");
    } finally {
      setChecking(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh" }}>
      <div
        style={{
          minHeight: 150,
          padding: 22,
          background:
            "linear-gradient(150deg,#caa97f 0%, #e2a290 55%, #ecb0a0 100%)",
          color: "#fff",
          borderRadius: "0 0 30px 30px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ fontSize: 23, fontWeight: 600, letterSpacing: 2 }}>
            {COPY.brandName}
          </div>
          <div
            style={{
              fontSize: 11,
              letterSpacing: 3,
              opacity: 0.85,
              marginTop: 3,
            }}
          >
            {COPY.brandSubtitle}
          </div>
        </div>
        <div
          style={{
            marginTop: 16,
            fontSize: 13,
            lineHeight: 1.6,
          }}
        >
          {COPY.homeHeroLine1}
          <br />
          {COPY.homeHeroLine2}
        </div>
      </div>

      <div style={{ padding: 16 }}>
        <div
          style={{
            fontSize: 14,
            color: "var(--ink-soft)",
            marginBottom: 20,
            lineHeight: 1.7,
          }}
        >
          {COPY.homeTagline}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
            marginBottom: 24,
          }}
        >
          {fourS.map((c) => (
            <div
              key={c.k}
              style={{
                background: "#fff",
                padding: 13,
                borderRadius: 16,
                boxShadow: "var(--shadow-soft)",
              }}
            >
              <div style={{ fontWeight: 700, color: "var(--gold-deep)" }}>
                {c.k}{" "}
                <span
                  style={{
                    fontSize: 10,
                    color: "var(--ink-light)",
                    fontWeight: 500,
                  }}
                >
                  {c.e}
                </span>
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--ink-soft)",
                  marginTop: 4,
                }}
              >
                {c.d}
              </div>
            </div>
          ))}
        </div>

        {resume && (
          <div
            onClick={goResume}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px 16px",
              marginBottom: 12,
              borderRadius: 16,
              cursor: "pointer",
              background: "rgba(200,163,118,0.12)",
              border: "1px solid rgba(200,163,118,0.4)",
            }}
          >
            <div style={{ lineHeight: 1.5 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--gold-deep)",
                }}
              >
                {resume.ready
                  ? "你有一份薇分美学4S报告已生成"
                  : "你有一份报告正在生成中"}
              </div>
              <div style={{ fontSize: 11, color: "var(--ink-soft)", marginTop: 2 }}>
                {resume.ready ? "点此查看报告" : "点此继续查看进度"}
              </div>
            </div>
            <span style={{ fontSize: 18, color: "var(--gold-deep)" }}>›</span>
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={checking}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            height: 48,
            borderRadius: 26,
            border: "none",
            cursor: checking ? "default" : "pointer",
            background: "linear-gradient(135deg,var(--gold),var(--rose))",
            color: "#fff",
            fontSize: 15,
            fontWeight: 600,
            boxShadow: "0 10px 24px rgba(200,163,118,0.36)",
          }}
        >
          {checking ? "检测中…" : "开始测一测"}
        </button>

        {blockMsg && (
          <div
            style={{
              marginTop: 12,
              fontSize: 13,
              color: "var(--danger)",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            {blockMsg}
          </div>
        )}

        <div
          style={{
            marginTop: 24,
            fontSize: 11,
            color: "var(--ink-light)",
            textAlign: "center",
            lineHeight: 1.7,
          }}
        >
          {COPY.disclaimerLine1}
          <br />
          {COPY.disclaimerLine2}
        </div>
      </div>
    </div>
  );
}
