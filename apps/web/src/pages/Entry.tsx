import { useMemo, useState } from "react";
import { QrCode } from "@/components/QrCode";
import { COPY } from "@/config/copy";

/**
 * 扫码入口页 —— 部署到阿里云后，此页面通常显示在门店 PC/平板 上，
 * 或印在物料 / 海报 / 名片背面。手机端相机 / 微信扫码后自动跳到 /login?src=qr。
 *
 * 支持通过 ?base=<url>&channel=<xx> 覆盖 QR 目标：
 *   /entry                            → 用当前 origin
 *   /entry?channel=poster-a           → 追加 utm 参数
 *   /entry?base=https://xx.com        → 强制目标域名（本地调试指向线上）
 */
export default function Entry() {
  const [channel, setChannel] = useState<string>(() => {
    const p = new URLSearchParams(window.location.search);
    return p.get("channel") || "";
  });
  const [baseOverride] = useState<string | null>(() => {
    const p = new URLSearchParams(window.location.search);
    return p.get("base");
  });

  const target = useMemo(() => {
    const base = baseOverride || window.location.origin;
    const url = new URL("/login", base);
    url.searchParams.set("src", "qr");
    if (channel.trim()) url.searchParams.set("channel", channel.trim());
    return url.toString();
  }, [baseOverride, channel]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(160deg,#fbf7f2 0%, #f5e9d8 60%, #f2d6c6 100%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "40px 24px 60px",
      }}
    >
      <div
        style={{
          fontSize: 24,
          fontWeight: 600,
          color: "#7a5a34",
          letterSpacing: 2,
        }}
      >
        {COPY.brandName}
      </div>
      <div
        style={{
          fontSize: 11,
          letterSpacing: 4,
          color: "#a37c40",
          marginTop: 6,
          opacity: 0.9,
        }}
      >
        {COPY.brandSubtitle}
      </div>

      <div
        style={{
          marginTop: 28,
          fontSize: 15,
          color: "#5b4a35",
          textAlign: "center",
          lineHeight: 1.7,
        }}
      >
        微信 / 相机 扫码开启你的
        <br />
        AI 薇分美学4S诊断
      </div>

      <div style={{ marginTop: 24 }}>
        <QrCode value={target} size={240} />
      </div>

      <div
        style={{
          marginTop: 20,
          fontSize: 12,
          color: "#8a7a66",
          textAlign: "center",
          wordBreak: "break-all",
          padding: "0 8px",
          maxWidth: 320,
        }}
      >
        {target}
      </div>

      <div
        style={{
          marginTop: 28,
          padding: 14,
          background: "rgba(255,255,255,0.7)",
          borderRadius: 12,
          maxWidth: 320,
          width: "100%",
        }}
      >
        <label
          style={{
            fontSize: 12,
            color: "#8a7a66",
            display: "block",
            marginBottom: 6,
          }}
        >
          渠道标记（可选，会追加到 URL）
        </label>
        <input
          type="text"
          placeholder="如：poster-a / card-2026 / event-618"
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
          style={{
            width: "100%",
            height: 36,
            padding: "0 10px",
            border: "1px solid #e6d4b6",
            borderRadius: 8,
            background: "#fff",
            fontSize: 13,
            outline: "none",
            boxSizing: "border-box",
          }}
        />
      </div>

      <div
        style={{
          marginTop: 30,
          fontSize: 11,
          color: "#b7a68e",
          textAlign: "center",
          lineHeight: 1.7,
          maxWidth: 320,
        }}
      >
        本报告为美学形象参考，不构成医疗诊断、治疗或术式建议
      </div>
    </div>
  );
}
