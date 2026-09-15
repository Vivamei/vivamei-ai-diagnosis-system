import { useState } from "react";
import { Navigate, useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useConsent } from "@/contexts/ConsentContext";
import { useCountdown } from "@/hooks/useCountdown";
import { SmsCodeInput } from "@/components/SmsCodeInput";
import { COPY } from "@/config/copy";

const PHONE_RE = /^1[3-9]\d{9}$/;

export default function Login() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const redirect = params.get("redirect") || "/";
  const src = params.get("src");

  const { sendCode, verifyCode, isLoggedIn } = useAuth();
  const { agreed, agree, currentVer } = useConsent();
  const cd = useCountdown();

  const [username, setUsername] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [consent, setConsent] = useState(agreed);
  const [err, setErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isLoggedIn) {
    return <Navigate to={redirect} replace />;
  }

  const canSend = PHONE_RE.test(phone) && cd.remaining === 0;
  const canSubmit =
    username.trim().length > 0 &&
    PHONE_RE.test(phone) &&
    /^\d{6}$/.test(code) &&
    consent &&
    !submitting;

  const onSend = async () => {
    setErr(null);
    if (!consent) {
      setErr("请先勾选同意《隐私政策》与《用户协议》");
      return;
    }
    try {
      await sendCode(phone);
      cd.start(60);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "发送失败");
    }
  };

  const onSubmit = async () => {
    setErr(null);
    if (!consent) {
      setErr("请先勾选同意《隐私政策》与《用户协议》");
      return;
    }
    setSubmitting(true);
    try {
      if (!agreed) agree();
      await verifyCode(phone, code, currentVer, username.trim());
      nav(redirect, { replace: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#fbf7f2" }}>
      <div
        style={{
          height: 200,
          padding: 22,
          background:
            "linear-gradient(150deg,#caa97f 0%, #e2a290 55%, #ecb0a0 100%)",
          color: "#fff",
          borderRadius: "0 0 30px 30px",
        }}
      >
        <div style={{ fontSize: 23, fontWeight: 600, letterSpacing: 2 }}>
          {COPY.brandName}
        </div>
        <div
          style={{
            fontSize: 11,
            letterSpacing: 3,
            opacity: 0.85,
            marginTop: 3,
          }}
        >
          {COPY.brandSubtitle}
        </div>
        <div style={{ marginTop: 46, fontSize: 15, opacity: 0.95 }}>
          {src === "qr" ? "扫码欢迎你 · 请先登录" : "登录后开始薇分美学4S体验"}
        </div>
      </div>

      <div
        style={{
          margin: "-40px 16px 0",
          padding: 20,
          background: "#fff",
          borderRadius: 20,
          boxShadow: "var(--shadow-soft, 0 8px 24px rgba(200,163,118,0.16))",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <label style={{ fontSize: 12, color: "var(--ink-soft,#8a7a66)" }}>
          用户名
        </label>
        <input
          type="text"
          placeholder="请输入昵称"
          value={username}
          maxLength={32}
          onChange={(e) => setUsername(e.target.value)}
          style={inputStyle}
          aria-label="用户名"
        />

        <label
          style={{
            fontSize: 12,
            color: "var(--ink-soft,#8a7a66)",
            marginTop: 4,
          }}
        >
          手机号
        </label>
        <input
          type="tel"
          inputMode="numeric"
          placeholder="请输入 11 位手机号"
          value={phone}
          maxLength={11}
          onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
          style={inputStyle}
          aria-label="手机号"
        />

        <label
          style={{
            fontSize: 12,
            color: "var(--ink-soft,#8a7a66)",
            marginTop: 4,
          }}
        >
          验证码
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ flex: 1 }}>
            <SmsCodeInput onComplete={setCode} />
          </div>
          <button
            type="button"
            disabled={!canSend}
            onClick={onSend}
            style={{
              minWidth: 120,
              borderRadius: 12,
              border: "1px solid var(--gold-light,#e6d4b6)",
              background: canSend ? "#fff" : "#f5efe5",
              color: canSend ? "var(--gold-deep,#a37c40)" : "#bbb",
              cursor: canSend ? "pointer" : "not-allowed",
              fontSize: 13,
            }}
          >
            {cd.remaining > 0 ? `${cd.remaining}s` : "获取验证码"}
          </button>
        </div>

        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            marginTop: 8,
            fontSize: 12,
            color: "var(--ink-soft,#8a7a66)",
            lineHeight: 1.6,
          }}
        >
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            style={{ marginTop: 3 }}
          />
          <span>
            我已阅读并同意
            <Link to="/legal/privacy" style={linkStyle}>《隐私政策》</Link>
            与
            <Link to="/legal/terms" style={linkStyle}>《用户协议》</Link>
          </span>
        </label>

        <button
          type="button"
          disabled={!canSubmit}
          onClick={onSubmit}
          style={{
            marginTop: 8,
            height: 46,
            borderRadius: 24,
            border: "none",
            background: canSubmit
              ? "linear-gradient(135deg,var(--gold,#caa97f),var(--rose,#e2a290))"
              : "#e7dccb",
            color: "#fff",
            fontWeight: 600,
            fontSize: 15,
            cursor: canSubmit ? "pointer" : "not-allowed",
            boxShadow: canSubmit
              ? "0 10px 24px rgba(200,163,118,0.36)"
              : "none",
          }}
        >
          {submitting ? "登录中…" : "登录"}
        </button>

        {err && (
          <div
            style={{
              color: "var(--danger,#d9534f)",
              fontSize: 13,
              marginTop: 4,
            }}
          >
            {err}
          </div>
        )}
      </div>

      <div
        style={{
          textAlign: "center",
          fontSize: 11,
          color: "var(--ink-light,#b7a68e)",
          marginTop: 24,
          padding: "0 24px",
          lineHeight: 1.7,
        }}
      >
        {COPY.disclaimerLine1}
        <br />
        {COPY.disclaimerLine2}
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  height: 44,
  padding: "0 14px",
  border: "1px solid var(--gold-light,#e6d4b6)",
  borderRadius: 12,
  fontSize: 15,
  background: "#fbf7f0",
  outline: "none",
};

const linkStyle: React.CSSProperties = {
  color: "var(--gold-deep,#a37c40)",
  textDecoration: "none",
};
