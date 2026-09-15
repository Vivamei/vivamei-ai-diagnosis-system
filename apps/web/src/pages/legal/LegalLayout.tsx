import { useNavigate } from "react-router-dom";
import { CSSProperties, ReactNode, useEffect } from "react";
import { COPY } from "@/config/copy";

export interface TocItem {
  id: string;
  label: string;
}

interface LegalLayoutProps {
  title: string;
  version: string;
  effectiveDate: string;
  toc: TocItem[];
  contactEmail: string;
  children: ReactNode;
}

const wrap: CSSProperties = {
  padding: "20px 16px 40px",
  minHeight: "100vh",
  background: "var(--bg-warm)",
};

const hero: CSSProperties = {
  background: "linear-gradient(135deg, #3a342c 0%, #4d443a 100%)",
  borderRadius: 18,
  padding: "28px 22px 22px",
  color: "#f0e6d5",
  boxShadow: "var(--shadow-card)",
  marginBottom: 16,
  position: "relative",
  overflow: "hidden",
};

const heroBrand: CSSProperties = {
  fontSize: 12,
  letterSpacing: 4,
  color: "var(--gold-light)",
  marginBottom: 10,
  fontWeight: 500,
};

const heroTitle: CSSProperties = {
  fontSize: 26,
  fontWeight: 700,
  letterSpacing: 4,
  margin: 0,
};

const heroDivider: CSSProperties = {
  width: 36,
  height: 2,
  background: "linear-gradient(90deg, var(--gold), var(--rose))",
  margin: "14px 0 12px",
  borderRadius: 1,
};

const badgeRow: CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
};

const badge: CSSProperties = {
  fontSize: 11,
  padding: "4px 10px",
  borderRadius: 12,
  border: "1px solid rgba(200,163,118,0.35)",
  color: "var(--gold-light)",
  background: "rgba(200,163,118,0.08)",
  letterSpacing: 0.5,
};

const tocCard: CSSProperties = {
  background: "var(--bg-card)",
  borderRadius: 14,
  padding: "16px 18px",
  boxShadow: "var(--shadow-soft)",
  marginBottom: 16,
  border: "1px solid var(--line)",
};

const tocTitle: CSSProperties = {
  fontSize: 12,
  letterSpacing: 2,
  color: "var(--ink-soft)",
  marginBottom: 10,
  fontWeight: 600,
};

const tocList: CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: 0,
  display: "flex",
  flexDirection: "column",
  gap: 6,
};

const tocLink: CSSProperties = {
  fontSize: 13,
  color: "var(--ink)",
  textDecoration: "none",
  padding: "6px 0",
  display: "flex",
  alignItems: "center",
  gap: 8,
  lineHeight: 1.4,
};

const tocDot: CSSProperties = {
  width: 5,
  height: 5,
  borderRadius: "50%",
  background: "var(--gold)",
  flexShrink: 0,
};

const contentCard: CSSProperties = {
  background: "var(--bg-card)",
  borderRadius: 14,
  padding: "8px 20px 24px",
  boxShadow: "var(--shadow-soft)",
  border: "1px solid var(--line)",
  marginBottom: 16,
};

const footer: CSSProperties = {
  marginTop: 20,
  paddingTop: 20,
  borderTop: "1px solid var(--line)",
  display: "flex",
  flexDirection: "column",
  gap: 14,
  alignItems: "center",
  color: "var(--ink-soft)",
  fontSize: 12,
};

const backBtn: CSSProperties = {
  height: 40,
  padding: "0 26px",
  borderRadius: 20,
  border: "1px solid var(--gold-light)",
  background: "transparent",
  color: "var(--gold-deep)",
  fontWeight: 600,
  fontSize: 13,
  cursor: "pointer",
};

export function LegalLayout({
  title,
  version,
  effectiveDate,
  toc,
  contactEmail,
  children,
}: LegalLayoutProps) {
  const navigate = useNavigate();

  useEffect(() => {
    if (!window.location.hash) return;
    const id = window.location.hash.slice(1);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  return (
    <div style={wrap}>
      <section style={hero}>
        <div style={heroBrand}>{COPY.brandSubtitle}</div>
        <h1 style={heroTitle}>{title}</h1>
        <div style={heroDivider} />
        <div style={badgeRow}>
          <span style={badge}>版本 {version}</span>
          <span style={badge}>生效日期 {effectiveDate}</span>
        </div>
      </section>

      <nav style={tocCard} aria-label="目录">
        <div style={tocTitle}>目录</div>
        <ul style={tocList}>
          {toc.map((item) => (
            <li key={item.id}>
              <a
                href={`#${item.id}`}
                style={tocLink}
                onClick={(e) => {
                  e.preventDefault();
                  const el = document.getElementById(item.id);
                  if (el)
                    el.scrollIntoView({ behavior: "smooth", block: "start" });
                  history.replaceState(null, "", `#${item.id}`);
                }}
              >
                <span style={tocDot} />
                <span>{item.label}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <article style={contentCard}>{children}</article>

      <footer style={footer}>
        <div>如有疑问或申诉,请联系 {contactEmail}</div>
        <div>© {COPY.brandName} · {COPY.brandSubtitle}</div>
        <button style={backBtn} onClick={() => navigate(-1)}>
          返回
        </button>
      </footer>
    </div>
  );
}

// 章节标题:h2 + 锚点 id + 金色装饰
export function LegalSection({
  id,
  index,
  title,
  children,
}: {
  id: string;
  index: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      style={{
        paddingTop: 22,
        marginTop: 8,
        scrollMarginTop: 16,
      }}
    >
      <h2
        style={{
          fontSize: 17,
          fontWeight: 700,
          color: "var(--ink)",
          margin: 0,
          marginBottom: 6,
          display: "flex",
          alignItems: "baseline",
          gap: 10,
        }}
      >
        <span
          style={{
            fontSize: 12,
            letterSpacing: 2,
            color: "var(--gold-deep)",
            fontWeight: 600,
          }}
        >
          {index}
        </span>
        <span>{title}</span>
      </h2>
      <div
        style={{
          width: 24,
          height: 2,
          background: "var(--gold)",
          borderRadius: 1,
          marginBottom: 14,
        }}
      />
      <div
        style={{
          fontSize: 14,
          lineHeight: 1.9,
          color: "var(--ink)",
        }}
      >
        {children}
      </div>
    </section>
  );
}

// 项目列表:自定义金色 dot,替代默认 marker
export function LegalList({ children }: { children: ReactNode }) {
  return (
    <ul
      style={{
        listStyle: "none",
        padding: 0,
        margin: "8px 0",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {children}
    </ul>
  );
}

export function LegalItem({ children }: { children: ReactNode }) {
  return (
    <li
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        fontSize: 14,
        lineHeight: 1.75,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: "var(--gold)",
          marginTop: 9,
          flexShrink: 0,
        }}
      />
      <span style={{ flex: 1 }}>{children}</span>
    </li>
  );
}

// 表格:柔和边框 + 金色表头
export function LegalTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | ReactNode)[][];
}) {
  return (
    <div
      style={{
        margin: "12px 0",
        borderRadius: 10,
        overflow: "hidden",
        border: "1px solid var(--line)",
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 13,
        }}
      >
        <thead>
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                style={{
                  background: "var(--bg-soft)",
                  color: "var(--ink)",
                  padding: "10px 12px",
                  textAlign: "left",
                  fontWeight: 600,
                  fontSize: 12,
                  letterSpacing: 0.5,
                  borderBottom: "1px solid var(--gold-light)",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={idx}
              style={{
                borderTop: idx === 0 ? "none" : "1px solid var(--line)",
              }}
            >
              {row.map((cell, i) => (
                <td
                  key={i}
                  style={{
                    padding: "10px 12px",
                    verticalAlign: "top",
                    color: "var(--ink)",
                    lineHeight: 1.6,
                  }}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 重点提示框:金色左边框 + 米色底
export function LegalCallout({
  tone = "info",
  children,
}: {
  tone?: "info" | "warning";
  children: ReactNode;
}) {
  const border =
    tone === "warning" ? "var(--rose-deep)" : "var(--gold-deep)";
  const bg = tone === "warning" ? "var(--bg-rose)" : "var(--bg-soft)";
  return (
    <div
      style={{
        margin: "14px 0",
        padding: "14px 16px",
        borderLeft: `3px solid ${border}`,
        background: bg,
        borderRadius: "6px 10px 10px 6px",
        fontSize: 13,
        lineHeight: 1.8,
        color: "var(--ink)",
      }}
    >
      {children}
    </div>
  );
}
