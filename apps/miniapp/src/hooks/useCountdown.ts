import { useEffect, useRef, useState } from 'react'

/** 短信验证码倒计时。start(60) 后每秒递减到 0。 */
export function useCountdown() {
  const [remaining, setRemaining] = useState(0)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current)
    },
    [],
  )

  const start = (seconds: number) => {
    setRemaining(seconds)
    if (timer.current) clearInterval(timer.current)
    timer.current = setInterval(() => {
      setRemaining((n) => {
        if (n <= 1) {
          if (timer.current) clearInterval(timer.current)
          return 0
        }
        return n - 1
      })
    }, 1000)
  }

  return { remaining, start }
}
