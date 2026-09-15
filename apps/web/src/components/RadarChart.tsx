import type { Phase } from "@/hooks/useSse";

interface Props {
  scores: { stype: number; style: number; subzone: number; struct: number };
  // 图下方 2×2 展示的数值（贵方 radar_chart.state_values，状态分，越高越年轻）。
  // 与 scores（轴长，越小越年轻）是两套口径；缺省时回落到 scores。
  legendScores?: {
    stype: number;
    style: number;
    subzone: number;
    struct: number;
  } | null;
  // 刻度上限，由贵方 radar_chart.max 给出；缺省 100（旧口径得分制）
  max?: number;
  onAxisClick?: (axis: Phase) => void;
}

// 顶点/图例色（对齐原型：分相 橙、分型 红、分区 绿、分层 蓝）
const AXIS_COLORS: Record<Phase, string> = {
  stype: "#c99048",
  style: "#cc5f4f",
  subzone: "#7a8f5a",
  struct: "#5a7896",
};

// 4 轴：上 分相 / 左 分型 / 右 分区 / 下 分层
const AXIS_META: Record<Phase, { cn: string; en: string; angle: number }> = {
  stype: { cn: "分相", en: "Stype", angle: -90 },
  style: { cn: "分型", en: "Style", angle: 180 },
  subzone: { cn: "分区", en: "Subzone", angle: 0 },
  struct: { cn: "分层", en: "Struct", angle: 90 },
};

// legend & label 展示顺序（对齐原型 2×2）
const AXES: Phase[] = ["stype", "style", "subzone", "struct"];
// polygon 连线顺序（几何顺时针，避免连出蝴蝶结）
const POLY_AXES: Phase[] = ["stype", "subzone", "struct", "style"];

const W = 300;
const H = 280;
const CX = W / 2;
const CY = H / 2;
const R = 84;

const polar = (angleDeg: number, r: number) => {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
};

export function RadarChart({ scores, legendScores, max = 100, onAxisClick }: Props) {
  const scaleMax = max > 0 ? max : 100;
  const legend = legendScores ?? scores;
  const vertexPos = (k: Phase) =>
    polar(
      AXIS_META[k].angle,
      (R * Math.max(0, Math.min(scaleMax, scores[k]))) / scaleMax,
    );

  const polyString = POLY_AXES.map((k) => {
    const p = vertexPos(k);
    return `${p.x},${p.y}`;
  }).join(" ");

  return (
    <div>
      {/* 居中不依赖任何 CSS 居中逻辑（flex/text-align/margin:auto 在 html2canvas 里都不稳）：
          让 SVG block + width:100% 直接铺满容器，内容本就对称于 viewBox 中线(x=W/2)，
          由 preserveAspectRatio(xMidYMid) 保证内容居中，容器多宽都不会偏。
          不设 maxWidth——一旦设了、容器更宽时 SVG 被钉成固定宽再靠 CSS 居中，就是偏移根因。
          overflow 保持默认 hidden：所有标签坐标都在 0..W/0..H 内，无需 visible。 */}
      <div>
        <svg
          width={W}
          height={H}
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
          style={{
            display: "block",
            width: "100%",
            height: "auto",
          }}
        >
        {/* 5 层圆环刻度（对应 max 的 20% / 40% / 60% / 80% / 100%） */}
        {[1.0, 0.8, 0.6, 0.4, 0.2].map((f, i) => (
          <circle
            key={i}
            cx={CX}
            cy={CY}
            r={R * f}
            fill="none"
            stroke="#e6ddd0"
            strokeOpacity={0.55 + (1 - f) * 0.15}
            strokeWidth={1}
          />
        ))}

        {/* 轴向虚线引导（从圆心到 4 个顶点） */}
        {AXES.map((k) => {
          const p = polar(AXIS_META[k].angle, R);
          return (
            <line
              key={k}
              x1={CX}
              y1={CY}
              x2={p.x}
              y2={p.y}
              stroke="#d8ccbb"
              strokeWidth={0.8}
              strokeDasharray="2 3"
              strokeOpacity={0.6}
            />
          );
        })}

        {/* 数据菱形（透明底 + 金色描边） */}
        <polygon
          points={polyString}
          fill="rgba(200,163,118,0.15)"
          stroke="#a37c40"
          strokeWidth={1.8}
          strokeLinejoin="round"
        />

        {/* 顶点彩色小圆 */}
        {AXES.map((k) => {
          const p = vertexPos(k);
          return (
            <circle
              key={k}
              cx={p.x}
              cy={p.y}
              r={4.5}
              fill={AXIS_COLORS[k]}
              stroke="#fff"
              strokeWidth={1.6}
            />
          );
        })}

        {/* 外侧轴标签（CN 竖排 EN，避免长英文溢出 viewBox） */}
        {AXES.map((k) => {
          const m = AXIS_META[k];
          const isVertical = m.angle === -90 || m.angle === 90;
          // 上/下轴标签放外侧；左/右靠近轴末端，anchor 用 middle 避免溢出
          const labelR = isVertical ? R + 24 : R + 22;
          const base = polar(m.angle, labelR);
          // 两行文字的中心 y：CN 在上，EN 在下
          const y1 = base.y - 7;
          const y2 = base.y + 8;
          return (
            <g
              key={k}
              style={{
                cursor: onAxisClick ? "pointer" : undefined,
                userSelect: "none",
              }}
              onClick={() => onAxisClick?.(k)}
            >
              <text
                x={base.x}
                y={y1}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="13"
                fontWeight="700"
                fill="#3a342c"
              >
                {m.cn}
              </text>
              <text
                x={base.x}
                y={y2}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="10"
                fontWeight="400"
                fill="#8c7e6e"
                letterSpacing="1"
              >
                {m.en}
              </text>
            </g>
          );
        })}
        </svg>
      </div>

      {onAxisClick && (
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "#a89a86",
            letterSpacing: 1,
            marginTop: 8,
          }}
        >
          点击任一维度查看该维度明细
        </div>
      )}

      {/* 2×2 数值图例（可点击进入该维度明细） */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          marginTop: 14,
        }}
      >
        {AXES.map((k) => (
          <div
            key={k}
            role={onAxisClick ? "button" : undefined}
            tabIndex={onAxisClick ? 0 : undefined}
            onClick={() => onAxisClick?.(k)}
            onKeyDown={(e) => {
              if (onAxisClick && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                onAxisClick(k);
              }
            }}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 14px",
              background: "#f7f0e3",
              borderRadius: 12,
              border: "1px solid rgba(200,163,118,0.15)",
              cursor: onAxisClick ? "pointer" : "default",
              userSelect: "none",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 4,
                  background: AXIS_COLORS[k],
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 13, color: "#3a342c" }}>
                {AXIS_META[k].cn}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                style={{
                  fontSize: 15,
                  color: "#3a342c",
                  fontWeight: 700,
                  letterSpacing: 0.5,
                }}
              >
                {legend[k]}
              </span>
              {onAxisClick && (
                <span style={{ fontSize: 15, color: "#c8a376" }}>›</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
