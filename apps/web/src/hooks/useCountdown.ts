import { useEffect, useRef, useState } from "react";

export function useCountdown() {
  const [remaining, setRemaining] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
    },
    [],
  );

  return {
    remaining,
    start: (seconds: number) => {
      setRemaining(seconds);
      if (timer.current) clearInterval(timer.current);
      timer.current = setInterval(() => {
        setRemaining((r) => {
          if (r <= 1) {
            if (timer.current) clearInterval(timer.current);
            return 0;
          }
          return r - 1;
        });
      }, 1000);
    },
  };
}
