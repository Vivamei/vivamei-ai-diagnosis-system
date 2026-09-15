import { createContext, useContext, useState, ReactNode } from "react";

const CURRENT_VER = "v1.0";

interface ConsentState {
  currentVer: string;
  agreed: boolean;
  agree: () => void;
}

const Ctx = createContext<ConsentState | null>(null);

export function ConsentProvider({ children }: { children: ReactNode }) {
  const [agreed, setAgreed] = useState(
    () => localStorage.getItem("venus.consent") === CURRENT_VER,
  );
  return (
    <Ctx.Provider
      value={{
        currentVer: CURRENT_VER,
        agreed,
        agree: () => {
          localStorage.setItem("venus.consent", CURRENT_VER);
          setAgreed(true);
        },
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useConsent = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error("ConsentProvider missing");
  return v;
};
