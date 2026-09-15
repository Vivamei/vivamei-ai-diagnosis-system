import { useState } from "react";

interface Props {
  onComplete: (code: string) => void;
}

export function SmsCodeInput({ onComplete }: Props) {
  const [val, setVal] = useState("");
  return (
    <input
      type="text"
      inputMode="numeric"
      pattern="\d{6}"
      maxLength={6}
      value={val}
      onChange={(e) => {
        const v = e.target.value.replace(/\D/g, "").slice(0, 6);
        setVal(v);
        if (v.length === 6) onComplete(v);
      }}
      style={{
        fontSize: 22,
        letterSpacing: 8,
        textAlign: "center",
        width: "100%",
        padding: 12,
        border: "1px solid var(--gold-light)",
        borderRadius: 12,
      }}
      role="textbox"
      aria-label="短信验证码"
    />
  );
}
