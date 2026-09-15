import { COPY } from "@/config/copy";

export function DisclaimerFooter() {
  return (
    <div
      style={{
        padding: "20px 16px 32px",
        textAlign: "center",
        fontSize: 11,
        color: "var(--ink-light)",
        lineHeight: 1.7,
      }}
    >
      {COPY.reportDisclaimerLine1}
      <br />
      {COPY.reportDisclaimerLine2}
    </div>
  );
}
