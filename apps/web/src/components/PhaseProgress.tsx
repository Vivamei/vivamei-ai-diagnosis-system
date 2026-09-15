import type { Phase, PhaseStatus } from "@/hooks/useSse";

const labels: Record<Phase, string> = {
  stype: "分相",
  style: "分型",
  subzone: "分区",
  struct: "分层",
};

interface Props {
  states: Record<Phase, { status: PhaseStatus }>;
}

export function PhaseProgress({ states }: Props) {
  const phases: Phase[] = ["style", "stype", "subzone", "struct"];
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "16px 14px",
        background: "#fff",
        borderRadius: 14,
        boxShadow: "var(--shadow-soft)",
      }}
    >
      {phases.map((p, i) => {
        const s = states[p].status;
        const isLast = i === phases.length - 1;
        const nextActive =
          !isLast &&
          (states[phases[i + 1]].status !== "idle" || s === "done");
        return (
          <div
            key={p}
            style={{
              flex: isLast ? "0 0 auto" : 1,
              display: "flex",
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
                minWidth: 44,
                transition: "transform 0.3s ease",
                transform: s === "streaming" ? "scale(1.08)" : "scale(1)",
              }}
            >
              <div
                style={{
                  width: 30,
                  height: 30,
                  lineHeight: "30px",
                  borderRadius: 15,
                  textAlign: "center",
                  color: "#fff",
                  fontSize: 12,
                  fontWeight: 700,
                  background:
                    s === "done"
                      ? "linear-gradient(135deg,#a5c8b6,#88b09a)"
                      : s === "streaming"
                        ? "linear-gradient(135deg,#e8d5b3,#c8a376)"
                        : "#d8ccbb",
                  animation:
                    s === "streaming" ? "pulseGold 1.5s infinite" : undefined,
                  transition: "background 0.4s ease",
                }}
              >
                {s === "done" ? "✓" : i + 1}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: s === "idle" ? "var(--ink-light)" : "var(--ink-soft)",
                  fontWeight: s === "streaming" ? 600 : 400,
                  transition: "color 0.3s ease",
                }}
              >
                {labels[p]}
              </div>
            </div>
            {!isLast && (
              <div
                style={{
                  flex: 1,
                  height: 2,
                  margin: "0 6px",
                  marginBottom: 22,
                  borderRadius: 1,
                  background: nextActive
                    ? "linear-gradient(90deg,#c8a376 0%,#c8a376 50%,#e8d5b3 50%,#e8d5b3 100%)"
                    : "#eee1cf",
                  backgroundSize: "24px 100%",
                  animation: nextActive ? "flowLine 0.9s linear infinite" : undefined,
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
