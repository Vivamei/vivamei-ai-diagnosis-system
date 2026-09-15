import { useCallback, useEffect, useRef, useState } from "react";
import Pica from "pica";

interface Props {
  onPicked: (
    file: Blob,
    info: { width: number; height: number; bytes: number },
  ) => void;
  disabled?: boolean;
}

const pica = Pica();
const MAX_EDGE = 1920;
const TARGET_BYTES = 1_000_000;

async function compressCanvas(
  source: HTMLCanvasElement,
): Promise<{ blob: Blob; width: number; height: number }> {
  const ratio = Math.min(1, MAX_EDGE / Math.max(source.width, source.height));
  const w = Math.round(source.width * ratio);
  const h = Math.round(source.height * ratio);

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  await pica.resize(source, canvas);
  let quality = 0.85;
  let blob = await pica.toBlob(canvas, "image/jpeg", quality);
  while (blob.size > TARGET_BYTES && quality > 0.5) {
    quality -= 0.1;
    blob = await pica.toBlob(canvas, "image/jpeg", quality);
  }
  return { blob, width: w, height: h };
}

// 强制页内相机实时拍摄，不提供相册上传入口，保证采集来源可控（精准性）
export function PhotoCapture({ onPicked, disabled }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [facing, setFacing] = useState<"user" | "environment">("user");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const start = useCallback(async () => {
    setErr(null);
    setReady(false);
    if (!navigator.mediaDevices?.getUserMedia) {
      setErr("当前环境不支持相机拍摄，请在支持的浏览器中打开（需 HTTPS）。");
      return;
    }
    try {
      stop();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: facing,
          width: { ideal: 1920 },
          height: { ideal: 1920 },
        },
        audio: false,
      });
      streamRef.current = stream;
      const v = videoRef.current;
      if (v) {
        v.srcObject = stream;
        await v.play().catch(() => {});
      }
      setReady(true);
    } catch (e) {
      const name = e instanceof DOMException ? e.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setErr("相机权限被拒绝。请在浏览器设置中允许相机权限后重试。");
      } else if (name === "NotFoundError") {
        setErr("未检测到可用摄像头。");
      } else {
        setErr("相机启动失败，请重试。");
      }
    }
  }, [facing, stop]);

  useEffect(() => {
    start();
    return stop;
  }, [start, stop]);

  const shoot = useCallback(async () => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    setBusy(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = v.videoWidth;
      canvas.height = v.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("canvas 不可用");
      // 前置仅预览镜像，落图保持真实方向
      ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
      const { blob, width, height } = await compressCanvas(canvas);
      stop();
      onPicked(blob, { width, height, bytes: blob.size });
    } catch {
      setErr("拍摄失败，请重试。");
      setBusy(false);
    }
  }, [onPicked, stop]);

  if (err) {
    return (
      <div
        style={{
          background: "#1c1815",
          border: "1px solid rgba(200,163,118,0.25)",
          borderRadius: 16,
          padding: 20,
          textAlign: "center",
          color: "#e6dcc9",
        }}
      >
        <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 14 }}>
          {err}
        </div>
        <button
          onClick={start}
          style={{
            height: 42,
            padding: "0 24px",
            borderRadius: 22,
            border: "1px solid #c8a376",
            background: "transparent",
            color: "#c8a376",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "3 / 4",
          borderRadius: 16,
          overflow: "hidden",
          background: "#000",
          border: "1px solid rgba(200,163,118,0.25)",
        }}
      >
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: facing === "user" ? "scaleX(-1)" : "none",
          }}
        />
        {!ready && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(240,230,213,0.7)",
              fontSize: 13,
            }}
          >
            相机启动中…
          </div>
        )}
        <button
          onClick={() =>
            setFacing((f) => (f === "user" ? "environment" : "user"))
          }
          disabled={busy}
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            height: 34,
            padding: "0 14px",
            borderRadius: 17,
            border: "1px solid rgba(240,230,213,0.4)",
            background: "rgba(28,24,21,0.5)",
            color: "#f0e6d5",
            fontSize: 12,
            cursor: busy ? "not-allowed" : "pointer",
            backdropFilter: "blur(4px)",
          }}
        >
          切换摄像头
        </button>
      </div>

      <button
        disabled={disabled || busy || !ready}
        onClick={shoot}
        style={{
          width: "100%",
          height: 48,
          marginTop: 14,
          borderRadius: 26,
          border: "none",
          color: "#fff",
          fontWeight: 600,
          background:
            disabled || !ready
              ? "var(--ink-light)"
              : "linear-gradient(135deg,var(--gold),var(--rose))",
          cursor: disabled || busy || !ready ? "not-allowed" : "pointer",
        }}
      >
        {busy ? "处理中…" : "拍摄"}
      </button>
    </div>
  );
}
