"use client"

import { createContext, useCallback, useContext, useState } from "react"
import { Toast } from "./Toast"

type ToastContextType = { showToast: (msg: string, duration?: number) => void }

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [message, setMessage] = useState<string | null>(null)
  const showToast = useCallback((msg: string, _duration?: number) => {
    setMessage(null)
    // slight delay to retrigger mount animation
    setTimeout(() => setMessage(msg), 10)
  }, [])
  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {message && <Toast message={message} />}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error("useToast must be used within ToastProvider")
  return ctx
}


