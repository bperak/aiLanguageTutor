"use client"

import { useEffect, useState } from "react"

type ToastType = "success" | "error" | "info" | "warning"

type ToastProps = { message: string; type?: ToastType; duration?: number }

const typeStyles: Record<ToastType, string> = {
  success: "bg-green-600 text-white",
  error: "bg-red-600 text-white",
  info: "bg-blue-600 text-white",
  warning: "bg-yellow-600 text-white",
}

export function Toast({ message, type = "info", duration = 3000 }: ToastProps) {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    const t = setTimeout(() => setVisible(false), duration)
    return () => clearTimeout(t)
  }, [duration])
  if (!visible) return null
  return (
    <div className={`fixed bottom-4 right-4 ${typeStyles[type]} px-3 py-2 rounded text-sm shadow-lg opacity-90 animate-in fade-in slide-in-from-bottom-4`}>
      {message}
    </div>
  )
}


