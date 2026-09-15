import { useState } from "react";

interface Props {
  onAgree: () => void;
  onCancel: () => void;
}

export function ConsentDialog({ onAgree, onCancel }: Props) {
  const [checked, setChecked] = useState(false);
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "flex-end",
        zIndex: 999,
      }}
    >
      <div
        style={{
          background: "#fff",
          width: "100%",
          maxWidth: 420,
          margin: "0 auto",
          borderRadius: "16px 16px 0 0",
          padding: 24,
          maxHeight: "85vh",
          overflowY: "auto",
        }}
      >
        <h3 style={{ fontSize: 18, marginBottom: 12 }}>
          隐私协议与人脸采集授权
        </h3>
        <div
          style={{
            fontSize: 13,
            color: "var(--ink-soft)",
            lineHeight: 1.7,
            marginBottom: 16,
          }}
        >
          <p>本服务需收集您的：</p>
          <ul style={{ paddingLeft: 18, margin: "8px 0" }}>
            <li>面部照片（用于 AI 薇分美学4S诊断分析，分析后 10 天内自动删除）</li>
            <li>手机号（用于身份验证与到店预约联系）</li>
          </ul>
          <p>
            详见{" "}
            <a href="/legal/privacy" target="_blank" rel="noreferrer">
              《隐私政策》
            </a>{" "}
            与{" "}
            <a href="/legal/terms" target="_blank" rel="noreferrer">
              《用户协议》
            </a>
            。
          </p>
          <p style={{ marginTop: 8, color: "var(--danger)" }}>
            本报告为美学形象参考，不构成医疗诊断、治疗或术式建议。
          </p>
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 16,
            fontSize: 13,
          }}
        >
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          我已阅读并同意以上协议
        </label>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1,
              height: 44,
              borderRadius: 22,
              background: "#fff",
              color: "var(--ink-soft)",
              border: "1.5px solid var(--gold-light)",
              cursor: "pointer",
            }}
          >
            取消
          </button>
          <button
            disabled={!checked}
            onClick={onAgree}
            style={{
              flex: 2,
              height: 44,
              borderRadius: 22,
              border: "none",
              color: "#fff",
              background: checked
                ? "linear-gradient(135deg,var(--gold),var(--rose))"
                : "var(--ink-light)",
              fontWeight: 600,
              cursor: checked ? "pointer" : "not-allowed",
            }}
          >
            同意并继续
          </button>
        </div>
      </div>
    </div>
  );
}
