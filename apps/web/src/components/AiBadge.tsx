export function AiBadge() {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 10,
        fontSize: 10,
        background: "var(--bg-soft)",
        color: "var(--gold-deep)",
        fontWeight: 600,
      }}
    >
      AI 生成 · 仅供参考
    </span>
  );
}
