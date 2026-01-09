"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { apiGet } from "@/lib/api"

type Me = { username: string; email: string }

export default function ProfilePage() {
  const router = useRouter()
  const [me, setMe] = useState<Me | null>(null)

  useEffect(() => {
    const t = localStorage.getItem("token")
    if (!t) { router.replace("/login"); return }
    apiGet<Me>("/api/v1/auth/me").then(setMe).catch(() => router.replace("/login"))
  }, [router])

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Profile</h1>
      {me ? (
        <div className="space-y-2">
          <div><span className="font-medium">Username:</span> {me.username}</div>
          <div><span className="font-medium">Email:</span> {me.email}</div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Loading...</p>
      )}
    </div>
  )
}


