"use client"

import { useEffect, useState } from "react"

type ToastProps = { message: string; duration?: number }

export function Toast({ message, duration = 3000 }: ToastProps) {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    const t = setTimeout(() => setVisible(false), duration)
    return () => clearTimeout(t)
  }, [duration])
  if (!visible) return null
  return (
    <div className="fixed bottom-4 right-4 bg-black text-white px-3 py-2 rounded text-sm shadow-lg opacity-90 animate-in fade-in slide-in-from-bottom-4">
      {message}
    </div>
  )
}


