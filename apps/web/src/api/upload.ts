import { apiFetch, AuthStore, ApiError } from "./client";

export interface StsResp {
  ossEndpoint: string;
  accessKeyId: string;
  accessKeySecret: string;
  securityToken: string;
  expiration: string;
  objectKey: string;
  maxBytes: number;
}

export const getUploadToken = () =>
  apiFetch<StsResp>("/api/upload/token", { method: "POST", body: "{}" });

// 未配 OSS 时的本地直传：走 multipart，必须绕开 apiFetch（其强制 JSON content-type
// 会破坏浏览器自动生成的 multipart boundary），用原生 fetch 手动带 Bearer。
export async function uploadLocal(objectKey: string, blob: Blob): Promise<void> {
  const form = new FormData();
  form.append("objectKey", objectKey);
  form.append("file", blob, "upload.jpg");
  const t = AuthStore.tokens;
  const res = await fetch("/api/upload/local", {
    method: "POST",
    headers: t ? { Authorization: `Bearer ${t.accessToken}` } : {},
    body: form,
  });
  if (!res.ok) {
    let body: Record<string, unknown> = {};
    try {
      body = await res.json();
    } catch {
      // 忽略解析失败，仍抛错
    }
    throw new ApiError(
      (body.code as string) || "UPLOAD_LOCAL_FAILED",
      (body.message as string) || res.statusText,
      res.status,
      body.requestId as string | undefined,
    );
  }
}

export interface PhotoMeta {
  ossKey: string;
  width?: number;
  height?: number;
  bytes?: number;
  mime?: string;
}

export const registerPhoto = (p: PhotoMeta) =>
  apiFetch<{ photoId: number; moderationStatus: string }>("/api/photos", {
    method: "POST",
    body: JSON.stringify(p),
  });
