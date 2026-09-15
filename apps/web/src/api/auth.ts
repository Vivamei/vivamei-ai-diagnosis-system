import { apiFetch, AuthStore, Tokens } from "./client";

export async function smsSend(phone: string) {
  return apiFetch<{ expiresIn: number }>("/api/auth/sms/send", {
    method: "POST",
    body: JSON.stringify({ phone, scene: "login" }),
  });
}

export interface VerifyResp extends Tokens {
  user: { id: number; nickname: string | null };
}

export async function smsVerify(
  phone: string,
  code: string,
  consentVer: string,
  username?: string,
): Promise<VerifyResp> {
  const data = await apiFetch<VerifyResp>("/api/auth/sms/verify", {
    method: "POST",
    body: JSON.stringify({ phone, code, consentVer, username }),
  });
  AuthStore.setTokens(data);
  AuthStore.setUser(data.user);
  return data;
}

export async function logout() {
  const t = AuthStore.tokens;
  if (t) {
    try {
      await apiFetch("/api/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refreshToken: t.refreshToken }),
      });
    } catch {
      // 失败也清本地
    }
  }
  AuthStore.clear();
}
