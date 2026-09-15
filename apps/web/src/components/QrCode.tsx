import { QRCodeSVG } from "qrcode.react";

interface Props {
  value: string;
  size?: number;
  logo?: string;
}

export function QrCode({ value, size = 220, logo }: Props) {
  return (
    <div
      style={{
        padding: 14,
        background: "#fff",
        borderRadius: 16,
        boxShadow: "0 8px 24px rgba(200,163,118,0.16)",
        display: "inline-block",
      }}
    >
      <QRCodeSVG
        value={value}
        size={size}
        level="M"
        marginSize={2}
        {...(logo
          ? {
              imageSettings: {
                src: logo,
                height: Math.round(size * 0.18),
                width: Math.round(size * 0.18),
                excavate: true,
              },
            }
          : {})}
      />
    </div>
  );
}
