"use client"

import useSWR from "swr"
import { apiGet } from "@/lib/api"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { getToken } from "@/lib/auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts"

type Dashboard = {
  user_id: string
  total_sessions: number
  total_messages: number
  last_session_at?: string | null
}

const fetcher = (url: string) => apiGet<Dashboard>(url)
type SessionSummary = { id: string; title?: string | null; total_messages?: number; created_at: string }
const sessionsFetcher = (url: string) => apiGet<SessionSummary[]>(url)
type SeriesPoint = { date?: string; week?: string; count: number }

export default function DashboardPage() {
  const router = useRouter()
  useEffect(() => {
    if (!getToken()) {
      router.replace("/login")
    }
  }, [router])
  const { data, error, isLoading } = useSWR("/api/v1/learning/dashboard", fetcher)
  const { data: sessions } = useSWR("/api/v1/conversations/sessions?limit=5", sessionsFetcher)
  const { data: messagesPerDay } = useSWR("/api/v1/analytics/messages_per_day?days=14", (u: string) => apiGet<SeriesPoint[]>(u))
  const { data: sessionsPerWeek } = useSWR("/api/v1/analytics/sessions_per_week?weeks=8", (u: string) => apiGet<SeriesPoint[]>(u))

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 p-4 sm:p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl sm:text-3xl font-semibold mb-4">Your Learning Dashboard</h1>
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse">
            <div className="h-28 rounded bg-slate-200" />
            <div className="h-28 rounded bg-slate-200" />
            <div className="h-28 rounded bg-slate-200" />
          </div>
        )}
        {error && <p className="text-sm text-destructive">Failed to load dashboard. Please sign in again.</p>}
        {data && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Total Sessions</CardTitle>
                <CardDescription>All time</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{data.total_sessions}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Total Messages</CardTitle>
                <CardDescription>All time</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{data.total_messages}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Last Session</CardTitle>
                <CardDescription>Most recent</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{data.last_session_at ? new Date(data.last_session_at).toLocaleDateString() : "—"}</p>
              </CardContent>
            </Card>
          </div>
        )}
        {(messagesPerDay || sessionsPerWeek) && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Messages per day</CardTitle>
                <CardDescription>Last 14 days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={messagesPerDay ?? []} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                      <XAxis dataKey="date" hide />
                      <YAxis allowDecimals={false} width={30} />
                      <Tooltip formatter={(v) => [v, "Messages"]} labelFormatter={(l) => `Date: ${l}`} />
                      <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Sessions per week</CardTitle>
                <CardDescription>Last 8 weeks</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sessionsPerWeek ?? []} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                      <XAxis dataKey="week" hide />
                      <YAxis allowDecimals={false} width={30} />
                      <Tooltip formatter={(v) => [v, "Sessions"]} labelFormatter={(l) => `Week: ${l}`} />
                      <Bar dataKey="count" fill="#10b981" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        {sessions && sessions.length > 0 && (
          <div className="mt-6">
            <h2 className="text-lg font-semibold mb-2">Recent Sessions</h2>
            <div className="grid gap-3">
              {sessions.map((s) => (
                <Card key={s.id}>
                  <CardHeader>
                    <CardTitle className="text-base">{s.title || "Untitled"}</CardTitle>
                    <CardDescription>{new Date(s.created_at).toLocaleString()}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm">Messages: {s.total_messages ?? 0}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
        {!isLoading && sessions && sessions.length === 0 && (
          <p className="mt-6 text-sm text-muted-foreground">No recent sessions yet. Start a conversation to see analytics here.</p>
        )}
      </div>
    </div>
  )
}


