import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";
import { getReport } from "@/api/analyze";
import { ApiError } from "@/api/client";
import { RadarChart } from "@/components/RadarChart";
import { AiBadge } from "@/components/AiBadge";
import { BrandHeader } from "@/components/BrandHeader";
import { DisclaimerFooter } from "@/components/DisclaimerFooter";
import { ReportExport } from "@/components/ReportExport";
import { COPY } from "@/config/copy";

interface ZoneItem {
  code: string;
  label: string;
  score?: number;
  status?: string;
  description: string;
  strength?: string;
  optimization?: string;
}
interface LayerItem {
  code: string;
  label: string;
  score?: number;
  status?: string;
  description: string;
  optimization?: string;
}
interface AestheticOpt {
  summary?: string;
  directions?: string[];
}
interface MappedDirection {
  direction?: string;
  display_title?: string;
  safe_description?: string;
  consult_note?: string;
}

const LAYER_COLOR: Record<string, string> = {
  skin: "#e8b04f",
  subcutis: "#d47a6a",
  fascia: "#88b09a",
  bone: "#c8a376",
};

// 3 类衰老相型（对齐报价单：骨相 / 肉相 / 皮相）
const STYPE_STAGES: { key: string; label: string; aliases: string[] }[] = [
  { key: "skin", label: "皮相", aliases: ["skin", "皮相", "皮相主导"] },
  { key: "flesh", label: "肉相", aliases: ["flesh", "肉相", "肉相主导"] },
  { key: "bone", label: "骨相", aliases: ["bone", "骨相", "骨相主导"] },
];

// 分相星级项（贵方 style_reference.composition，后端已把 soft_tissue 映射成 flesh）
interface CompositionItem {
  label?: string;
  stars?: number;
  max_stars?: number;
}

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const { data, error, isLoading } = useSWR(
    id ? `/api/reports/${id}` : null,
    () => getReport(id!),
  );

  if (isLoading)
    return <div style={{ padding: 40, textAlign: "center" }}>加载中…</div>;
  if (error) return <ReportError error={error} onRetry={() => nav("/")} />;
  if (!data) return null;

  const stypePrimary =
    (data.stype.primary as string) || (data.stype.label as string) || "";
  const stypeLabel = (data.stype.label as string) || "";
  const stypeText =
    (data.stype.description as string) ||
    (data.stype.narrative as string) ||
    "";
  const stypeEvidence = (data.stype.evidence as string[]) || [];
  const stypeRatios = (data.stype.ratios as Record<string, number>) || null;
  const stypeComposition =
    (data.stype.composition as Record<string, CompositionItem>) || null;
  const stypeScore = data.stype.score as number | undefined;

  const styleLabel =
    (data.style.label as string) ||
    (data.style.primary_label as string) ||
    "";
  const styleText =
    (data.style.description as string) ||
    (data.style.narrative as string) ||
    "";
  const styleKeywords = (data.style.keywords as string[]) || [];
  const styleScore = data.style.score as number | undefined;

  const subzoneSummary = (data.subzone.summary as string) || "";
  const subzoneZones = (data.subzone.zones as ZoneItem[]) || [];
  const subzoneScore = data.subzone.score as number | undefined;

  const structSummary = (data.struct.summary as string) || "";
  const structLayers = (data.struct.layers as LayerItem[]) || [];
  const structScore = data.struct.score as number | undefined;

  // 贵方新口径：radarScores 是轴长（衰老差距），越小越年轻；图下方 4S 数值另取
  // state_values（状态分，越高越年轻）。两者都由贵方直接给出，本方不换算。
  // 分型不参与衰老计算，其轴值固定在高位，故文案需单独说明。
  // 旧口径（radar_semantics 缺省）雷达图仍是得分，越高越好。
  const agingExposure =
    data.radar_semantics === "aging_exposure" ||
    data.radar_semantics === "four_s_state_gap_index";

  const aOpt = (data.aesthetic_optimization as AestheticOpt) || {};
  const projectDirections = (data.project_directions as string[]) || [];
  const mappedDirections =
    (data.mapped_project_directions as MappedDirection[]) || [];

  return (
    <div style={{ padding: 16, paddingBottom: 32 }} id="report-root">
      <BrandHeader right={<AiBadge />} />

      {/* P1 · 4S 雷达图 */}
      <Section variant="light">
        <div
          style={{
            textAlign: "center",
            fontSize: 18,
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          {COPY.brandName} 4S 雷达图
        </div>
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "var(--ink-soft)",
            marginTop: 4,
            letterSpacing: 2,
            marginBottom: 8,
          }}
        >
          {agingExposure
            ? "图形越小越年轻 · 分型不参与衰老评估"
            : "四维评估体系 · 精准定位衰老维度"}
        </div>
        <RadarChart
          scores={data.radarScores}
          legendScores={data.state_values}
          max={data.radar_max ?? 100}
          onAxisClick={(axis) => nav(`/report/${id}/${axis}`)}
        />
      </Section>

      {/* P2 · 分型诊断 */}
      <Section>
        <SectionTitle cn="分型诊断" en="Style" score={styleScore} />
        {styleLabel && (
          <div
            style={{
              fontSize: 15,
              fontWeight: 700,
              color: "#c8a376",
              marginTop: 14,
            }}
          >
            {styleLabel}
          </div>
        )}
        <div
          style={{
            fontSize: 13,
            lineHeight: 1.75,
            color: "#e6dcc9",
            marginTop: 14,
          }}
        >
          {styleText}
        </div>
        {styleKeywords.length > 0 && (
          <div
            style={{
              marginTop: 12,
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
            }}
          >
            {styleKeywords.map((k) => (
              <span key={k} style={darkTagStyle}>
                {k}
              </span>
            ))}
          </div>
        )}
      </Section>

      {/* P2 · 分相诊断 */}
      <Section>
        <SectionTitle cn="分相诊断" en="Stype" score={stypeScore} />
        <StypeTimeline
          primary={stypePrimary}
          ratios={stypeRatios}
          composition={stypeComposition}
        />
        <div
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: "#c8a376",
            marginTop: 4,
          }}
        >
          {stypeLabel}
        </div>
        <div
          style={{
            fontSize: 13,
            lineHeight: 1.75,
            color: "#e6dcc9",
            marginTop: 6,
          }}
        >
          {stypeText}
        </div>
        {stypeEvidence.length > 0 && (
          <ul
            style={{
              marginTop: 10,
              paddingLeft: 18,
              fontSize: 12,
              lineHeight: 1.75,
              color: "rgba(240,230,213,0.7)",
            }}
          >
            {stypeEvidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </Section>

      {/* P3 · 分区评估 */}
      <Section>
        <SectionTitle cn="分区评估" en="Subzone" score={subzoneScore} />
        <div
          style={{
            fontSize: 11,
            color: "rgba(240,230,213,0.55)",
            marginTop: 2,
            marginBottom: 12,
          }}
        >
          按美学分区，逐单位精准诊断
        </div>
        {subzoneSummary && (
          <div
            style={{
              fontSize: 12,
              color: "rgba(240,230,213,0.7)",
              marginBottom: 12,
              lineHeight: 1.75,
            }}
          >
            {subzoneSummary}
          </div>
        )}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
          }}
        >
          {subzoneZones.slice(0, 6).map((z) => (
            <div
              key={z.code}
              style={{
                background: "rgba(200,163,118,0.08)",
                border: "1px solid rgba(200,163,118,0.2)",
                borderRadius: 12,
                padding: 12,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  justifyContent: "space-between",
                  gap: 6,
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#e6dcc9",
                  }}
                >
                  {z.label}
                </span>
                {typeof z.score === "number" && (
                  <span style={{ fontSize: 12, color: "#e8c477" }}>
                    {z.score}
                  </span>
                )}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "rgba(240,230,213,0.6)",
                  lineHeight: 1.6,
                  marginTop: 4,
                }}
              >
                {z.description}
              </div>
              {z.strength && (
                <div
                  style={{
                    fontSize: 10,
                    color: "#88b09a",
                    lineHeight: 1.6,
                    marginTop: 6,
                  }}
                >
                  优势 · {z.strength}
                </div>
              )}
              {z.optimization && (
                <div
                  style={{
                    fontSize: 10,
                    color: "#d9b892",
                    lineHeight: 1.6,
                    marginTop: 4,
                  }}
                >
                  优化 · {z.optimization}
                </div>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* P3 · 分层评估 */}
      <Section>
        <SectionTitle cn="分层评估" en="Struct" score={structScore} />
        <div
          style={{
            fontSize: 11,
            color: "rgba(240,230,213,0.55)",
            marginTop: 2,
            marginBottom: 12,
          }}
        >
          按结构层次评估，指导分层结构干预
        </div>
        {structSummary && (
          <div
            style={{
              fontSize: 12,
              color: "rgba(240,230,213,0.7)",
              marginBottom: 12,
              lineHeight: 1.75,
            }}
          >
            {structSummary}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {structLayers.map((l) => {
            const color = LAYER_COLOR[l.code] || "#c8a376";
            const pct = Math.max(0, Math.min(100, l.score ?? 0));
            return (
              <div key={l.code}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12,
                    marginBottom: 4,
                  }}
                >
                  <span style={{ color: "#e6dcc9" }}>{l.label}</span>
                  <span style={{ color, fontWeight: 700 }}>{l.score ?? "—"}</span>
                </div>
                <div
                  style={{
                    height: 6,
                    background: "rgba(240,230,213,0.1)",
                    borderRadius: 3,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${pct}%`,
                      background: color,
                      borderRadius: 3,
                      transition: "width 0.6s ease",
                    }}
                  />
                </div>
                {(l.status || l.description) && (
                  <div
                    style={{
                      fontSize: 10,
                      color: "rgba(240,230,213,0.55)",
                      lineHeight: 1.6,
                      marginTop: 5,
                    }}
                  >
                    {l.status || l.description}
                  </div>
                )}
                {l.optimization && (
                  <div
                    style={{
                      fontSize: 10,
                      color: "#d9b892",
                      lineHeight: 1.6,
                      marginTop: 3,
                    }}
                  >
                    优化 · {l.optimization}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Section>

      {/* 美学优化方向 */}
      <div
        style={{
          marginTop: 12,
          background: "#fbf6ee",
          padding: 16,
          borderRadius: 16,
          border: "1px solid var(--gold-light)",
        }}
      >
        <div
          style={{
            fontWeight: 700,
            fontSize: 13,
            marginBottom: 8,
            color: "var(--gold-deep)",
          }}
        >
          美学优化方向
        </div>
        <div
          style={{
            fontSize: 13,
            color: "var(--ink-soft)",
            lineHeight: 1.75,
          }}
        >
          {aOpt.summary || data.optimization}
        </div>
        {aOpt.directions && aOpt.directions.length > 0 && (
          <ul
            style={{
              marginTop: 10,
              paddingLeft: 18,
              color: "var(--ink-soft)",
              fontSize: 12,
              lineHeight: 1.75,
            }}
          >
            {aOpt.directions.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        )}
      </div>

      {projectDirections.length > 0 && (
        <div
          style={{
            marginTop: 12,
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
          }}
        >
          {projectDirections.map((t) => (
            <span key={t} style={lightTagStyle}>
              {t}
            </span>
          ))}
        </div>
      )}

      {mappedDirections.length > 0 && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
          {mappedDirections.map((m, i) => (
            <div
              key={i}
              style={{
                background: "#fff",
                border: "1px solid var(--line)",
                borderRadius: 16,
                padding: 14,
                boxShadow: "var(--shadow-soft)",
              }}
            >
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: "var(--gold-deep)",
                }}
              >
                {m.display_title || m.direction}
              </div>
              {m.safe_description && (
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--ink-soft)",
                    lineHeight: 1.75,
                    marginTop: 6,
                  }}
                >
                  {m.safe_description}
                </div>
              )}
              {m.consult_note && (
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--ink-soft)",
                    opacity: 0.75,
                    lineHeight: 1.6,
                    marginTop: 6,
                  }}
                >
                  {m.consult_note}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* CTA */}
      <div
        data-export-hide="1"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          marginTop: 20,
        }}
      >
        <div style={{ display: "flex", gap: 10 }}>
          <ReportExport sourceSelector="#report-root" taskId={id} />
        </div>
        {COPY.leadText && (
          <div
            style={{
              fontSize: 12,
              color: "var(--ink-soft)",
              textAlign: "center",
              padding: "0 8px",
              lineHeight: 1.6,
            }}
          >
            {COPY.leadText}
          </div>
        )}
        <button
          onClick={() => nav(`/booking?taskId=${id}`)}
          style={{
            width: "100%",
            height: 46,
            borderRadius: 24,
            border: "none",
            color: "#fff",
            fontWeight: 600,
            background:
              "linear-gradient(135deg,var(--gold),var(--gold-deep))",
            cursor: "pointer",
            boxShadow: "0 10px 24px rgba(200,163,118,0.36)",
          }}
        >
          {COPY.ctaReport}
        </button>
      </div>

      <DisclaimerFooter />
    </div>
  );
}

// ---------- sub components ----------

// 报告加载失败：停止 loading，直接给错误提示。
// 错误日志 + 原始错误返回信息打到浏览器控制台（后端也会写 log 文件）。
function ReportError({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const api = error instanceof ApiError ? error : null;
  const code = api?.code || "REPORT_LOAD_ERROR";
  const message =
    (error as Error)?.message || "报告加载失败，请稍后重试。";
  React.useEffect(() => {
    console.error("[report] 报告加载失败", {
      code,
      message,
      status: api?.status,
      requestId: api?.requestId,
      raw: error,
    });
  }, [error, api, code, message]);

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
          报告加载失败
        </h2>
        <p style={{ fontSize: 13, color: "#e6dcc9", margin: "0 0 6px" }}>
          {message}
        </p>
        <div
          style={{
            fontSize: 11,
            color: "var(--ink-soft)",
            marginBottom: 18,
            wordBreak: "break-all",
          }}
        >
          错误码：{code}
          {api?.requestId ? ` · 请求号：${api.requestId}` : ""}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
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
          <button
            onClick={onRetry}
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

function Section({
  children,
  variant = "dark",
}: {
  children: React.ReactNode;
  variant?: "dark" | "light";
}) {
  const dark = variant === "dark";
  return (
    <div
      style={{
        marginTop: 12,
        background: dark ? "#1c1815" : "#fff",
        padding: 18,
        borderRadius: 20,
        boxShadow: dark
          ? "0 12px 32px rgba(28,24,21,0.28)"
          : "var(--shadow-soft)",
        border: dark
          ? "1px solid rgba(200,163,118,0.18)"
          : "1px solid var(--line)",
        color: dark ? "#e6dcc9" : "var(--ink)",
      }}
    >
      {children}
    </div>
  );
}

function SectionTitle({
  cn,
  en,
  score,
}: {
  cn: string;
  en: string;
  score?: number;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 8,
      }}
    >
      <span
        style={{
          fontSize: 15,
          fontWeight: 700,
          color: "#c8a376",
          letterSpacing: 0.5,
        }}
      >
        {cn}
      </span>
      <span
        style={{
          fontSize: 12,
          color: "rgba(240,230,213,0.55)",
          letterSpacing: 1,
        }}
      >
        · {en}
      </span>
      {typeof score === "number" && (
        <span
          style={{
            marginLeft: "auto",
            fontSize: 12,
            color: "#e8c477",
            letterSpacing: 0.5,
          }}
        >
          得分 <b style={{ fontSize: 15 }}>{score}</b>
        </span>
      )}
    </div>
  );
}

// 分相占比 → 星级：以三相中的最高占比为满 5 星，其余按比例折算（至少 1 星），
// 直观呈现「骨/肉/皮」各相的主导强弱，替代原先易被误读为流程的 1-2-3 步骤条。
function ratioToStars(ratio: number, maxRatio: number): number {
  if (!(maxRatio > 0)) return 1;
  return Math.max(1, Math.min(5, Math.round((ratio / maxRatio) * 5)));
}

function StarRow({ label, stars, active }: { label: string; stars: number; active: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "7px 0",
      }}
    >
      <span
        style={{
          minWidth: 42,
          fontSize: 13,
          fontWeight: active ? 700 : 500,
          color: active ? "#e8d5b3" : "rgba(240,230,213,0.7)",
        }}
      >
        {label}
      </span>
      <span style={{ letterSpacing: 3, fontSize: 16 }}>
        {[1, 2, 3, 4, 5].map((n) => (
          <span
            key={n}
            style={{ color: n <= stars ? "#e8c477" : "rgba(200,163,118,0.22)" }}
          >
            ★
          </span>
        ))}
      </span>
    </div>
  );
}

function StypeTimeline({
  primary,
  ratios,
  composition,
}: {
  primary: string;
  ratios: Record<string, number> | null;
  composition?: Record<string, CompositionItem> | null;
}) {
  const isActive = (s: (typeof STYPE_STAGES)[number]) =>
    s.aliases.some((a) => primary?.toLowerCase().includes(a.toLowerCase()));

  // 贵方直接给了三相星级（style_reference.composition）：星级即结论，无需再折算。
  // 星最多的一相视为主导相高亮，不依赖 primary（新版报告已不再返回 primary）。
  if (composition) {
    const rows = STYPE_STAGES.map((stage) => ({
      stage,
      item: composition[stage.key],
    }))
      .filter((r) => typeof r.item?.stars === "number")
      .sort((a, b) => (b.item!.stars ?? 0) - (a.item!.stars ?? 0));

    if (rows.length > 0) {
      const top = rows[0].item!.stars ?? 0;
      return (
        <div style={{ margin: "12px 0 4px" }}>
          {rows.map(({ stage, item }) => (
            <StarRow
              key={stage.key}
              label={item!.label || stage.label}
              stars={item!.stars ?? 0}
              active={(item!.stars ?? 0) === top}
            />
          ))}
        </div>
      );
    }
  }

  // 有占比数据：按星级呈现；从高到低排序，主导相在最上。
  if (ratios) {
    const maxRatio = Math.max(
      ...STYPE_STAGES.map((s) => ratios[s.key] ?? 0),
      0,
    );
    const rows = STYPE_STAGES.map((s) => ({
      stage: s,
      ratio: ratios[s.key] ?? 0,
    })).sort((a, b) => b.ratio - a.ratio);

    return (
      <div style={{ margin: "12px 0 4px" }}>
        {rows.map(({ stage, ratio }) => (
          <StarRow
            key={stage.key}
            label={stage.label}
            stars={ratioToStars(ratio, maxRatio)}
            active={isActive(stage)}
          />
        ))}
      </div>
    );
  }

  // 无占比数据：回退到原步骤条，仅高亮主导相。
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        margin: "14px 0 4px",
      }}
    >
      {STYPE_STAGES.map((s, i) => {
        const active = isActive(s);
        const isLast = i === STYPE_STAGES.length - 1;
        return (
          <React.Fragment key={s.key}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
                minWidth: 52,
              }}
            >
              <div
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: 15,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  background: active
                    ? "linear-gradient(135deg,#e8d5b3,#c8a376)"
                    : "rgba(200,163,118,0.12)",
                  color: active ? "#fff" : "rgba(240,230,213,0.5)",
                  border: active
                    ? "1px solid #c8a376"
                    : "1px solid rgba(200,163,118,0.25)",
                  boxShadow: active
                    ? "0 6px 16px rgba(200,163,118,0.4)"
                    : "none",
                }}
              >
                {i + 1}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: active ? "#c8a376" : "rgba(240,230,213,0.5)",
                  fontWeight: active ? 600 : 400,
                }}
              >
                {s.label}
              </div>
            </div>
            {!isLast && (
              <div
                style={{
                  flex: 1,
                  height: 2,
                  margin: "0 6px 22px",
                  background: "rgba(200,163,118,0.2)",
                  borderRadius: 1,
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

const darkTagStyle: React.CSSProperties = {
  padding: "4px 10px",
  background: "rgba(200,163,118,0.15)",
  color: "#e5d3b3",
  borderRadius: 12,
  fontSize: 12,
  border: "1px solid rgba(200,163,118,0.3)",
};

const lightTagStyle: React.CSSProperties = {
  padding: "4px 10px",
  background: "#fbf6ee",
  color: "var(--gold-deep)",
  borderRadius: 12,
  fontSize: 12,
  border: "1px solid var(--gold-light)",
};
