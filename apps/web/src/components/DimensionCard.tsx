import { useState, ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  children: ReactNode;
  defaultOpen?: boolean;
  variant?: "dark" | "light";
}

export function DimensionCard({
  title,
  subtitle,
  children,
  defaultOpen = true,
  variant = "dark",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const isDark = variant === "dark";
  return (
    <div
      style={{
        background: isDark ? "#1c1815" : "#fff",
        padding: 18,
        borderRadius: 20,
        boxShadow: isDark
          ? "0 12px 32px rgba(28, 24, 21, 0.28)"
          : "var(--shadow-soft)",
        border: isDark
          ? "1px solid rgba(200, 163, 118, 0.18)"
          : "1px solid var(--line)",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          width: "100%",
          background: "none",
          border: "none",
          padding: 0,
          cursor: "pointer",
          textAlign: "left",
          color: isDark ? "#f0e6d5" : "inherit",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 15,
              fontWeight: 700,
              color: isDark ? "#c8a376" : "var(--gold-deep)",
              letterSpacing: 0.5,
            }}
          >
            {title}
          </div>
          {subtitle && (
            <div
              style={{
                fontSize: 11,
                color: isDark ? "rgba(240,230,213,0.6)" : "var(--ink-soft)",
                marginTop: 3,
                letterSpacing: 0.4,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
        <span
          style={{
            color: isDark ? "rgba(240,230,213,0.5)" : "var(--ink-soft)",
          }}
        >
          {open ? "▴" : "▾"}
        </span>
      </button>
      {open && (
        <div
          style={{
            marginTop: 14,
            fontSize: 13,
            color: isDark ? "#e6dcc9" : "var(--ink)",
            lineHeight: 1.75,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
