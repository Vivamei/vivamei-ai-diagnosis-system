import { useState } from "react";

import { AuthStore } from "@/api/client";

interface Props {
  sourceSelector: string;
  taskId?: string;
}

type Kind = "png" | "pdf";

const WATERMARK = "AI 生成 · 仅供参考";

// 微信内置浏览器 / iOS Safari 禁用 <a download> 编程式下载，手机端一律走
// 「长按图片保存」浮层；桌面端才用锚点下载。
function isMobileLike(): boolean {
  const ua = navigator.userAgent || "";
  return /micromessenger|android|iphone|ipad|ipod|mobile/i.test(ua);
}

// iOS canvas 有面积/单边上限（保守取 4096px 单边、16M 面积），超限会出空图或
// toDataURL 抛错。按源尺寸把 scale 从 2 往下压到安全范围，保证手机也能导出。
function pickScale(el: HTMLElement): number {
  const w = el.offsetWidth || el.getBoundingClientRect().width || 1;
  const h = el.scrollHeight || el.getBoundingClientRect().height || 1;
  const MAX_SIDE = 4096;
  const MAX_AREA = 16_000_000;
  let scale = 2;
  scale = Math.min(scale, MAX_SIDE / w, MAX_SIDE / h);
  scale = Math.min(scale, Math.sqrt(MAX_AREA / (w * h)));
  return Math.max(1, scale);
}

async function renderSourceCanvas(
  selector: string,
): Promise<HTMLCanvasElement | null> {
  const el = document.querySelector(selector) as HTMLElement | null;
  if (!el) return null;
  const { default: html2canvas } = await import("html2canvas");
  const canvas = await html2canvas(el, {
    backgroundColor: "#fdfaf5",
    scale: pickScale(el),
    useCORS: true,
    // 导出时跳过带 data-export-hide 的元素（如 CTA 按钮区）
    ignoreElements: (node) =>
      node instanceof HTMLElement &&
      node.getAttribute("data-export-hide") === "1",
  });
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "rgba(58,52,44,0.5)";
    ctx.font = "14px sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(WATERMARK, canvas.width - 16, canvas.height - 12);
  }
  return canvas;
}

function triggerDownload(url: string, name: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // 立即 revoke 可能在下载启动前就把 blob 回收掉，延迟释放
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

async function savePng(
  canvas: HTMLCanvasElement,
  onPreview: (dataUrl: string) => void,
) {
  if (isMobileLike()) {
    // 手机端无法编程式下载，出图后让用户长按保存到相册
    onPreview(canvas.toDataURL("image/png"));
    return;
  }
  const blob = await new Promise<Blob | null>((r) =>
    canvas.toBlob(r, "image/png"),
  );
  if (!blob) throw new Error("toBlob returned null");
  triggerDownload(URL.createObjectURL(blob), `4s-report-${Date.now()}.png`);
}

// 从源 canvas 抽一片 y 区间生成新 canvas（用来分页贴 PDF）
function sliceCanvas(
  src: HTMLCanvasElement,
  sy: number,
  sh: number,
): HTMLCanvasElement | null {
  const c = document.createElement("canvas");
  c.width = src.width;
  c.height = sh;
  const ctx = c.getContext("2d");
  if (!ctx) return null;
  ctx.drawImage(src, 0, sy, src.width, sh, 0, 0, src.width, sh);
  return c;
}

function buildPdf(canvas: HTMLCanvasElement) {
  return import("jspdf").then(({ jsPDF }) => {
    // 单页长 PDF:页面宽 = A4 宽 210mm,高按 canvas 比例延长,整图一次贴入不切割
    const PAGE_W_MM = 210;
    const pxToMm = PAGE_W_MM / canvas.width;
    const pageH_mm = canvas.height * pxToMm;

    const pdf = new jsPDF({
      unit: "mm",
      format: [PAGE_W_MM, pageH_mm],
      orientation: "portrait",
    });

    // jsPDF 对超大单页 image 直接贴入可能因 canvas 尺寸过大而 OOM,分块贴避免爆内存
    const CHUNK_PX = 4000;
    let sy = 0;
    while (sy < canvas.height) {
      const sh = Math.min(CHUNK_PX, canvas.height - sy);
      const slice = sliceCanvas(canvas, sy, sh);
      if (!slice) break;
      const dataUrl = slice.toDataURL("image/jpeg", 0.92);
      pdf.addImage(dataUrl, "JPEG", 0, sy * pxToMm, PAGE_W_MM, sh * pxToMm);
      sy += sh;
    }
    return pdf;
  });
}

async function savePdf(
  canvas: HTMLCanvasElement,
  onMessage: (msg: string) => void,
  taskId?: string,
) {
  const pdf = await buildPdf(canvas);
  const name = `4s-report-${Date.now()}.pdf`;
  if (isMobileLike()) {
    // 手机端（尤其微信 webview）打不开 blob: URL，且 await 后 window.open 会被拦截。
    // 改为把 PDF 字节 POST 给后端存好，跳转后端返回的真实 http 下载链接（带 attachment 头）。
    if (!taskId) {
      onMessage(
        "无法在手机端直接下载 PDF，请改用「保存为长图」，或在电脑端打开保存。",
      );
      return;
    }
    const blob = pdf.output("blob") as Blob;
    const token = AuthStore.tokens?.accessToken;
    const res = await fetch(`/api/reports/${taskId}/pdf`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: blob,
    });
    if (!res.ok) throw new Error(`upload pdf failed: ${res.status}`);
    const { downloadUrl } = (await res.json()) as { downloadUrl: string };
    // attachment 响应触发下载、不卸载当前 SPA 页面；相对路径解析到当前 origin
    window.location.href = downloadUrl;
    return;
  }
  pdf.save(name);
}

export function ReportExport({ sourceSelector, taskId }: Props) {
  const [busy, setBusy] = useState<Kind | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const handle = async (kind: Kind) => {
    setBusy(kind);
    setMsg(null);
    try {
      const canvas = await renderSourceCanvas(sourceSelector);
      if (!canvas) {
        setMsg("未找到报告内容，请刷新后重试");
        return;
      }
      if (kind === "png") await savePng(canvas, setPreview);
      else await savePdf(canvas, setMsg, taskId);
    } catch (e) {
      console.error("[report-export] 导出失败", { kind, error: e });
      setMsg("生成失败，请稍后重试；如多次失败可尝试另一种格式。");
    } finally {
      setBusy(null);
    }
  };

  const baseStyle = {
    flex: 1,
    height: 44,
    borderRadius: 22,
    background: "#fff",
    border: "1.5px solid var(--gold-light)",
    color: "var(--gold-deep)",
    fontWeight: 600,
  } as const;

  const disabled = busy !== null;
  const cursor = disabled ? "not-allowed" : "pointer";

  return (
    <>
      <button
        onClick={() => handle("png")}
        disabled={disabled}
        style={{ ...baseStyle, cursor }}
      >
        {busy === "png" ? "生成中…" : "保存为长图"}
      </button>
      <button
        onClick={() => handle("pdf")}
        disabled={disabled}
        style={{ ...baseStyle, cursor }}
      >
        {busy === "pdf" ? "生成中…" : "保存为 PDF"}
      </button>

      {msg && (
        <div
          onClick={() => setMsg(null)}
          style={{
            position: "fixed",
            left: 16,
            right: 16,
            bottom: 24,
            zIndex: 60,
            background: "rgba(28,24,21,0.95)",
            color: "#f0e6d5",
            fontSize: 13,
            lineHeight: 1.6,
            padding: "12px 16px",
            borderRadius: 14,
            boxShadow: "0 12px 32px rgba(28,24,21,0.35)",
          }}
        >
          {msg}
        </div>
      )}

      {preview && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 80,
            background: "rgba(0,0,0,0.9)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              flexShrink: 0,
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              color: "#f0e6d5",
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            <span>长按图片保存到相册</span>
            <button
              onClick={() => setPreview(null)}
              style={{
                background: "none",
                border: "1px solid rgba(240,230,213,0.4)",
                color: "#f0e6d5",
                borderRadius: 16,
                padding: "4px 14px",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              关闭
            </button>
          </div>
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              WebkitOverflowScrolling: "touch",
              padding: "0 12px 24px",
              textAlign: "center",
            }}
          >
            <img
              src={preview}
              alt="4s 分析报告"
              style={{
                width: "100%",
                height: "auto",
                borderRadius: 10,
                boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
              }}
            />
          </div>
        </div>
      )}
    </>
  );
}
