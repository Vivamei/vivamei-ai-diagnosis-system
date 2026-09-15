import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useConsent } from "@/contexts/ConsentContext";
import { ConsentDialog } from "@/components/ConsentDialog";
import { PhotoCapture } from "@/components/PhotoCapture";
import { createAnalyze, LastTaskStore } from "@/api/analyze";
import { getUploadToken, registerPhoto, uploadLocal, StsResp } from "@/api/upload";

async function ossDirectPut(token: StsResp, blob: Blob): Promise<void> {
  // 未配 OSS（MOCK 凭证）时改传后端本地存储，让原图能到后端供分析上送 LLM。
  if (token.accessKeyId.startsWith("STS.MOCK")) {
    await uploadLocal(token.objectKey, blob);
    return;
  }
  const r = await fetch(`${token.ossEndpoint}/${token.objectKey}`, {
    method: "PUT",
    headers: {
      "x-oss-security-token": token.securityToken,
      "content-type": "image/jpeg",
      // 生产需补 OSS V4 签名 - M10 部署阶段建议用 ali-oss SDK 或 PostObject 表单
    },
    body: blob,
  });
  if (!r.ok) throw new Error(`OSS upload failed: ${r.status}`);
}

export default function Capture() {
  const nav = useNavigate();
  const { agreed, agree } = useConsent();

  const [showConsent, setShowConsent] = useState(!agreed);
  const [stage, setStage] = useState<"capture" | "uploading">("capture");
  const [err, setErr] = useState<string | null>(null);

  const handlePicked = async (
    blob: Blob,
    info: { width: number; height: number; bytes: number },
  ) => {
    setStage("uploading");
    setErr(null);
    try {
      const token = await getUploadToken();
      await ossDirectPut(token, blob);
      const photo = await registerPhoto({
        ossKey: token.objectKey,
        mime: "image/jpeg",
        ...info,
      });
      // 等待后端机审（mock 模式即时通过）
      await new Promise((r) => setTimeout(r, 700));
      const task = await createAnalyze(photo.photoId);
      // 记住这次任务，供中途离开后在首页找回（见 Home.tsx 的续看入口）
      LastTaskStore.save(task.taskId);
      nav(`/analyzing/${task.taskId}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "上传失败";
      setErr(msg);
      setStage("capture");
    }
  };

  return (
    <div style={{ padding: 16, minHeight: "100vh" }}>
      <h2 style={{ fontSize: 18, marginBottom: 16 }}>开始薇分美学4S测评</h2>

      {stage === "capture" && (
        <div>
          <div
            style={{
              background: "#fbf6ee",
              border: "1px solid var(--gold-light)",
              padding: 12,
              borderRadius: 12,
              fontSize: 12,
              color: "var(--ink-soft)",
              marginBottom: 16,
              lineHeight: 1.6,
            }}
          >
            建议自然光下正脸拍摄，去除眼镜与浓妆，分析效果更准。
          </div>
          <PhotoCapture onPicked={handlePicked} />
        </div>
      )}

      {stage === "uploading" && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "50px 20px",
            gap: 14,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "3px solid rgba(200,163,118,0.25)",
              borderTopColor: "#c8a376",
              animation: "spin 0.9s linear infinite",
            }}
          />
          <div style={{ color: "var(--ink-soft)", fontSize: 13 }}>
            正在上传并校验图像…
          </div>
        </div>
      )}

      {err && (
        <div
          style={{
            color: "var(--danger)",
            marginTop: 16,
            fontSize: 13,
          }}
        >
          {err}
        </div>
      )}

      {showConsent && (
        <ConsentDialog
          onAgree={() => {
            agree();
            setShowConsent(false);
          }}
          onCancel={() => nav("/")}
        />
      )}
    </div>
  );
}
