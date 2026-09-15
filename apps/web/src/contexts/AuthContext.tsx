import { createContext, useContext, useState, ReactNode } from "react";
import { AuthStore } from "@/api/client";
import {
  smsSend as apiSmsSend,
  smsVerify as apiSmsVerify,
  logout as apiLogout,
} from "@/api/auth";

interface User {
  id: number;
  nickname: string | null;
}

interface AuthState {
  isLoggedIn: boolean;
  user: User | null;
  sendCode: (phone: string) => Promise<void>;
  verifyCode: (
    phone: string,
    code: string,
    consentVer: string,
    username?: string,
  ) => Promise<void>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => AuthStore.user);
  const [tokenTick, setTokenTick] = useState(0);

  return (
    <Ctx.Provider
      value={{
        isLoggedIn: !!AuthStore.tokens && tokenTick >= 0,
        user,
        sendCode: async (phone) => {
          await apiSmsSend(phone);
        },
        verifyCode: async (phone, code, ver, username) => {
          const d = await apiSmsVerify(phone, code, ver, username);
          setUser(d.user);
          setTokenTick((n) => n + 1);
        },
        signOut: async () => {
          await apiLogout();
          setUser(null);
          setTokenTick((n) => n + 1);
        },
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error("AuthProvider missing");
  return v;
};
