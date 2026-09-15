import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createBooking } from "@/api/booking";

export default function Booking() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [store, setStore] = useState("");
  const [time, setTime] = useState("");
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (done)
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <div style={{ fontSize: 60 }}>✓</div>
        <div style={{ fontSize: 16, marginTop: 12 }}>预约提交成功</div>
        <button
          onClick={() => nav("/")}
          style={{
            marginTop: 24,
            padding: "10px 24px",
            borderRadius: 22,
            background: "linear-gradient(135deg,var(--gold),var(--rose))",
            color: "#fff",
            border: "none",
            cursor: "pointer",
          }}
        >
          返回首页
        </button>
      </div>
    );

  const formInvalid = !name || !/^1[3-9]\d{9}$/.test(phone);

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontSize: 18, marginBottom: 16 }}>预约到店面诊</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input
          placeholder="姓名"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{
            height: 44,
            padding: "0 14px",
            border: "1px solid var(--gold-light)",
            borderRadius: 12,
            fontSize: 15,
          }}
        />
        <input
          type="tel"
          inputMode="numeric"
          placeholder="手机号"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          style={{
            height: 44,
            padding: "0 14px",
            border: "1px solid var(--gold-light)",
            borderRadius: 12,
            fontSize: 15,
          }}
        />
        <input
          placeholder="门店编码（选填）"
          value={store}
          onChange={(e) => setStore(e.target.value)}
          style={{
            height: 44,
            padding: "0 14px",
            border: "1px solid var(--gold-light)",
            borderRadius: 12,
            fontSize: 15,
          }}
        />
        <input
          type="datetime-local"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          style={{
            height: 44,
            padding: "0 14px",
            border: "1px solid var(--gold-light)",
            borderRadius: 12,
            fontSize: 15,
          }}
        />
        <button
          disabled={formInvalid}
          onClick={async () => {
            try {
              await createBooking({
                name,
                phone,
                storeCode: store || undefined,
                appointmentAt: time ? new Date(time).toISOString() : undefined,
                taskId: sp.get("taskId") || undefined,
                source: sp.get("source") || undefined,
              });
              setDone(true);
            } catch (e) {
              setErr(e instanceof Error ? e.message : "提交失败");
            }
          }}
          style={{
            height: 48,
            borderRadius: 24,
            border: "none",
            color: "#fff",
            fontWeight: 600,
            background: formInvalid
              ? "var(--ink-light)"
              : "linear-gradient(135deg,var(--gold),var(--rose))",
            cursor: formInvalid ? "not-allowed" : "pointer",
          }}
        >
          提交预约
        </button>
        {err && (
          <div style={{ color: "var(--danger)", fontSize: 13 }}>{err}</div>
        )}
      </div>
    </div>
  );
}
