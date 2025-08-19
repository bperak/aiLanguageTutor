"use client"

import { useState } from "react"
import { apiPost } from "@/lib/api"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

type ScheduleResponse = { item_id: string; next_review_days: number; next_review_date: string }

export default function SRSDemoPage() {
  const [itemId, setItemId] = useState("word:日本")
  const [resp, setResp] = useState<ScheduleResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function schedule(grade: "again" | "hard" | "good" | "easy") {
    setLoading(true)
    try {
      const data = await apiPost<ScheduleResponse>("/api/v1/srs/schedule", {
        item_id: itemId,
        last_interval_days: 1,
        grade,
      })
      setResp(data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-3">SRS Schedule (Demo)</h1>
      <div className="flex items-center gap-2 mb-3">
        <Input value={itemId} onChange={(e) => setItemId(e.target.value)} className="max-w-sm" />
        <Button onClick={() => schedule("again")} disabled={loading}>Again</Button>
        <Button onClick={() => schedule("hard")} disabled={loading} variant="ghost">Hard</Button>
        <Button onClick={() => schedule("good")} disabled={loading} variant="ghost">Good</Button>
        <Button onClick={() => schedule("easy")} disabled={loading} variant="ghost">Easy</Button>
      </div>
      {resp && (
        <div className="text-sm text-muted-foreground">
          Next review in {resp.next_review_days} days ({new Date(resp.next_review_date).toLocaleDateString()})
        </div>
      )}
    </div>
  )
}


