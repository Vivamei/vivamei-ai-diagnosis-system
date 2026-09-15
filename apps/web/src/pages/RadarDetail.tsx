import { useParams, useNavigate } from "react-router-dom";
import useSWR from "swr";
import { getReport } from "@/api/analyze";
import { BrandHeader } from "@/components/BrandHeader";
import { DisclaimerFooter } from "@/components/DisclaimerFooter";
import { ReportExport } from "@/components/ReportExport";

const AXIS_META: Record<
  string,
  { cn: string; en: string; accent: string }
> = {
  stype: { cn: "分相", en: "Stype", accent: "#c99048" },
  style: { cn: "分型", en: "Style", accent: "#cc5f4f" },
  subzone: { cn: "分区", en: "Subzone", accent: "#7a8f5a" },
  struct: { cn: "分层", en: "Struct", accent: "#5a7896" },
};

interface ZoneItem {
  code: string;
  label: string;
  description: string;
  strength?: string;
  optimization?: string;
}
interface LayerItem {
  code: string;
  label: string;
  score?: number;
  description: string;
  optimization?: string;
}

export default function RadarDetail() {
  const { id, axis } = useParams<{ id: string; axis: string }>();
  const nav = useNavigate();
  const { data, error, isLoading } = useSWR(
    id ? `/api/reports/${id}` : null,
    () => getReport(id!),
  );

  if (!axis) return null;
  const meta = AXIS_META[axis];
  if (!meta) return null;

  const section = data
    ? (data as unknown as Record<string, Record<string, unknown>>)[axis]
    : undefined;

  const description =
    (section?.description as string) || (section?.narrative as string) || "";
  const label =
    (section?.label as string) || (section?.primary_label as string) || "";
  const score = section?.score as number | undefined;
  const summary = (section?.summary as string) || "";
  const evidence = (section?.evidence as string[]) || [];
  const keywords = (section?.keywords as string[]) || [];
  const zones = (section?.zones as ZoneItem[]) || [];
  const layers = (section?.layers as LayerItem[]) || [];

  const hasContent =
    !!description ||
    !!summary ||
    !!label ||
    evidence.length > 0 ||
    keywords.length > 0 ||
    zones.length > 0 ||
    layers.length > 0;

  return (
    <div style={{ padding: 16, paddingBottom: 32 }} id="detail-root">
      <BrandHeader
        right={
          <button
            onClick={() => nav(-1)}
            style={{
              background: "none",
              border: "none",
              color: "var(--ink-soft)",
              cursor: "pointer",
              padding: 0,
              fontSize: 13,
            }}
          >
            ← 返回
          </button>
        }
      />

      <div
        style={{
          textAlign: "center",
          fontSize: 17,
          fontWeight: 600,
          color: "var(--ink)",
          marginTop: 10,
        }}
      >
        分享你的美学报告
      </div>
      <div
        style={{
          textAlign: "center",
          fontSize: 11,
          color: "var(--ink-soft)",
          letterSpacing: 2,
          marginTop: 4,
          marginBottom: 14,
        }}
      >
        {meta.cn} · {meta.en}
      </div>

      {/* P4 · 大居中卡片 */}
      <div
        style={{
          background: "#1c1815",
          borderRadius: 22,
          padding: "28px 22px",
          boxShadow: "0 14px 36px rgba(28,24,21,0.28)",
          border: "1px solid rgba(200,163,118,0.18)",
          color: "#e6dcc9",
        }}
      >
        {isLoading && (
          <div
            style={{
              textAlign: "center",
              fontSize: 13,
              color: "rgba(240,230,213,0.7)",
              padding: "8px 0",
            }}
          >
            加载中…
          </div>
        )}
        {!isLoading && error && (
          <div
            style={{
              textAlign: "center",
              fontSize: 13,
              color: "#e0a1a1",
              padding: "8px 0",
              lineHeight: 1.7,
            }}
          >
            报告加载失败：{(error as Error).message}
          </div>
        )}
        {!isLoading && !error && !hasContent && (
          <div
            style={{
              textAlign: "center",
              fontSize: 13,
              color: "rgba(240,230,213,0.6)",
              padding: "8px 0",
            }}
          >
            暂无该维度明细
          </div>
        )}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: 14,
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 28,
              background: `linear-gradient(135deg, ${meta.accent}55, ${meta.accent}aa)`,
              border: `1px solid ${meta.accent}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              fontWeight: 700,
              color: "#fff",
              letterSpacing: 1,
              boxShadow: `0 8px 20px ${meta.accent}55`,
            }}
          >
            {meta.cn}
          </div>
        </div>

        <div
          style={{
            textAlign: "center",
            fontSize: 22,
            fontWeight: 700,
            color: "#f0e6d5",
            letterSpacing: 1,
          }}
        >
          {label || meta.cn}
        </div>
        {score != null && (
          <div
            style={{
              textAlign: "center",
              fontSize: 13,
              color: meta.accent,
              marginTop: 6,
              fontWeight: 600,
            }}
          >
            综合评分 {score}
          </div>
        )}

        {description && (
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.85,
              color: "#e6dcc9",
              marginTop: 18,
              textAlign: "justify",
            }}
          >
            {description}
          </div>
        )}
        {summary && (
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.85,
              color: "rgba(240,230,213,0.75)",
              marginTop: 12,
              textAlign: "justify",
            }}
          >
            {summary}
          </div>
        )}

        {/* 关键词 / 佐证 */}
        {keywords.length > 0 && (
          <div
            style={{
              marginTop: 18,
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              justifyContent: "center",
            }}
          >
            {keywords.map((k) => (
              <span
                key={k}
                style={{
                  padding: "4px 12px",
                  background: `${meta.accent}22`,
                  color: "#e5d3b3",
                  borderRadius: 14,
                  fontSize: 12,
                  border: `1px solid ${meta.accent}55`,
                }}
              >
                {k}
              </span>
            ))}
          </div>
        )}
        {evidence.length > 0 && (
          <ul
            style={{
              marginTop: 18,
              paddingLeft: 20,
              fontSize: 12,
              lineHeight: 1.85,
              color: "rgba(240,230,213,0.7)",
            }}
          >
            {evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}

        {/* 分区详情：6 个部位 */}
        {zones.length > 0 && (
          <div
            style={{
              marginTop: 18,
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {zones.map((z) => (
              <div
                key={z.code}
                style={{
                  padding: 12,
                  background: "rgba(200,163,118,0.08)",
                  border: "1px solid rgba(200,163,118,0.2)",
                  borderRadius: 12,
                }}
              >
                <div
                  style={{
                    color: meta.accent,
                    fontWeight: 700,
                    fontSize: 13,
                    marginBottom: 4,
                  }}
                >
                  {z.label}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "rgba(240,230,213,0.8)",
                    lineHeight: 1.7,
                  }}
                >
                  {z.description}
                </div>
                {(z.strength || z.optimization) && (
                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 11,
                      color: "rgba(240,230,213,0.55)",
                      lineHeight: 1.7,
                    }}
                  >
                    {z.strength && <div>· 优势：{z.strength}</div>}
                    {z.optimization && <div>· 优化：{z.optimization}</div>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 分层详情：4 层带独立评分 */}
        {layers.length > 0 && (
          <div
            style={{
              marginTop: 18,
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {layers.map((l) => (
              <div
                key={l.code}
                style={{
                  padding: 12,
                  background: "rgba(200,163,118,0.08)",
                  border: "1px solid rgba(200,163,118,0.2)",
                  borderRadius: 12,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      color: meta.accent,
                      fontWeight: 700,
                      fontSize: 13,
                    }}
                  >
                    {l.label}
                  </span>
                  {l.score != null && (
                    <span
                      style={{
                        color: meta.accent,
                        fontWeight: 700,
                        fontSize: 14,
                      }}
                    >
                      {l.score}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "rgba(240,230,213,0.8)",
                    lineHeight: 1.7,
                  }}
                >
                  {l.description}
                </div>
                {l.optimization && (
                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 11,
                      color: "rgba(240,230,213,0.55)",
                      lineHeight: 1.7,
                    }}
                  >
                    · 优化：{l.optimization}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 二维码占位：与 P4 一致的分享位 */}
        <div
          style={{
            marginTop: 22,
            padding: 14,
            background: "rgba(240,230,213,0.06)",
            border: "1px dashed rgba(200,163,118,0.3)",
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div
            style={{
              width: 60,
              height: 60,
              background: "rgba(240,230,213,0.1)",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 10,
              color: "rgba(240,230,213,0.5)",
            }}
          >
            二维码
          </div>
          <div
            style={{
              fontSize: 11,
              color: "rgba(240,230,213,0.55)",
              letterSpacing: 1,
            }}
          >
            扫码进入小程序 · 复制体验
          </div>
        </div>
      </div>

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
          <ReportExport sourceSelector="#detail-root" />
        </div>
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
          预约到店面诊
        </button>
      </div>

      <DisclaimerFooter />
    </div>
  );
}
