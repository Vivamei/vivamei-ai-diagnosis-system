import { ReactNode } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { COPY } from "@/config/copy";

export function BrandHeader({ right }: { right?: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 4px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <BrandLogo size={32} />
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "var(--ink)" }}>
            {COPY.brandName}
          </div>
          <div
            style={{
              fontSize: 9,
              color: "var(--ink-soft)",
              letterSpacing: 3,
            }}
          >
            {COPY.brandSubtitle}
          </div>
        </div>
      </div>
      {right}
    </div>
  );
}
