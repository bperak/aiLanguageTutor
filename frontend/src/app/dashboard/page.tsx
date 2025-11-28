"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function DashboardPage() {
  const router = useRouter()
  useEffect(() => {
    // Redirect to home page
    router.replace("/")
  }, [router])
  
  // Return null while redirecting
  return null
}
