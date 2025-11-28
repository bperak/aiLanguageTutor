"use client"

import { createContext, useCallback, useContext, useState } from "react"
import { Toast } from "./Toast"

type ToastType = "success" | "error" | "info" | "warning"

type ToastContextType = { showToast: (msg: string, type?: ToastType | number) => void }

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [message, setMessage] = useState<string | null>(null)
  const [type, setType] = useState<ToastType>("info")
  const showToast = useCallback((msg: string, typeOrDuration?: ToastType | number) => {
    setMessage(null)
    // Check if second parameter is a string (type) or number (duration)
    if (typeof typeOrDuration === "string") {
      setType(typeOrDuration)
    } else {
      setType("info")
    }
    // slight delay to retrigger mount animation
    setTimeout(() => setMessage(msg), 10)
  }, [])
  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {message && <Toast message={message} type={type} />}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error("useToast must be used within ToastProvider")
  return ctx
}


