export type Tokens = {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
};

export type StoredUser = {
  id: number;
  nickname: string | null;
};

// 「记住登录」最长天数。默认 7 天，对齐后端 JWT_REFRESH_TTL_SECONDS（604800s）。
// 两者应保持一致：后端 refresh token 到期后即便本地还留着也刷不出新 access token。
// 通过构建时 VITE_AUTH_MAX_AGE_DAYS 覆盖（改完需重打 web 镜像）。
const AUTH_MAX_AGE_DAYS = Number(import.meta.env.VITE_AUTH_MAX_AGE_DAYS) || 7;
const AUTH_MAX_AGE_MS = AUTH_MAX_AGE_DAYS * 24 * 60 * 60 * 1000;

// 登录态存 localStorage 并带首次登录时间戳（savedAt）：同一手机在有效期内（默认 30 天）
// 再次进来免登录，符合获客测评 H5 的业内惯例。超过 savedAt + 有效期即视为过期、自动清除，
// 下次扫码回到干净登录页；access token 刷新时保留 savedAt，不顺延这条绝对窗口。
type StoredTokens = Tokens & { savedAt: number };

class _AuthStore {
  private tokenKey = "venus.auth";
  private userKey = "venus.user";

  get tokens(): Tokens | null {
    const raw = localStorage.getItem(this.tokenKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredTokens;
    if (
      typeof parsed.savedAt === "number" &&
      Date.now() - parsed.savedAt > AUTH_MAX_AGE_MS
    ) {
      this.clear();
      return null;
    }
    return parsed;
  }

  // 登录成功：写入并盖上首次登录时间戳，开启一条固定的有效期窗口。
  setTokens(t: Tokens) {
    const stored: StoredTokens = { ...t, savedAt: Date.now() };
    localStorage.setItem(this.tokenKey, JSON.stringify(stored));
  }

  // 静默刷新 access token：保留原 savedAt / refreshToken，不顺延有效期窗口。
  updateAccessToken(accessToken: string, expiresIn: number) {
    const raw = localStorage.getItem(this.tokenKey);
    if (!raw) return;
    const prev = JSON.parse(raw) as StoredTokens;
    const next: StoredTokens = { ...prev, accessToken, expiresIn };
    localStorage.setItem(this.tokenKey, JSON.stringify(next));
  }

  get user(): StoredUser | null {
    const raw = localStorage.getItem(this.userKey);
    return raw ? JSON.parse(raw) : null;
  }

  setUser(u: StoredUser) {
    localStorage.setItem(this.userKey, JSON.stringify(u));
  }

  clear() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }
}

export const AuthStore = new _AuthStore();

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public requestId?: string,
  ) {
    super(message);
  }
}

let refreshing: Promise<Tokens> | null = null;

async function doRefresh(): Promise<Tokens> {
  const t = AuthStore.tokens;
  if (!t) throw new ApiError("AUTH_REQUIRED", "not logged in", 401);
  const r = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refreshToken: t.refreshToken }),
  });
  if (!r.ok) {
    AuthStore.clear();
    throw new ApiError("AUTH_REFRESH_FAILED", "refresh failed", r.status);
  }
  const data = await r.json();
  const merged: Tokens = {
    ...t,
    accessToken: data.accessToken,
    expiresIn: data.expiresIn,
  };
  AuthStore.updateAccessToken(data.accessToken, data.expiresIn);
  return merged;
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const t = AuthStore.tokens;
  const headers: Record<string, string> = {
    "content-type": "application/json",
    ...((init.headers as Record<string, string>) || {}),
    ...(t ? { Authorization: `Bearer ${t.accessToken}` } : {}),
  };

  let res = await fetch(path, { ...init, headers });

  // 401 时尝试 refresh 一次
  if (res.status === 401 && t) {
    refreshing ||= doRefresh().finally(() => {
      refreshing = null;
    });
    const fresh = await refreshing;
    res = await fetch(path, {
      ...init,
      headers: { ...headers, Authorization: `Bearer ${fresh.accessToken}` },
    });
  }

  if (!res.ok) {
    let body: Record<string, unknown> = {};
    try {
      body = await res.json();
    } catch {
      // body 解析失败时仍要抛错
    }
    throw new ApiError(
      (body.code as string) || "HTTP_ERROR",
      (body.message as string) || res.statusText,
      res.status,
      body.requestId as string | undefined,
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
