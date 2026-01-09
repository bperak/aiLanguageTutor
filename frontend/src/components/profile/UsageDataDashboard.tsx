"use client";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
type Dashboard = {
  user_id: string;
  total_sessions: number;
  total_messages: number;
  last_session_at?: string | null;
};
type SeriesPoint = { date?: string; week?: string; count: number };
export default function UsageDataDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [messagesPerDay, setMessagesPerDay] = useState<SeriesPoint[]>([]);
  const [sessionsPerWeek, setSessionsPerWeek] = useState<SeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);
  const loadData = async () => {
    try {
      const [dashboardData, messagesData, sessionsData] = await Promise.all([
        apiGet<Dashboard>("/api/v1/profile/usage-data/dashboard"),
        apiGet<SeriesPoint[]>("/api/v1/analytics/messages_per_day?days=14"),
        apiGet<SeriesPoint[]>("/api/v1/analytics/sessions_per_week?weeks=8"),
      ]);

      // Handle case where messagesData or sessionsData might be empty
      const messages = Array.isArray(messagesData) ? messagesData : [];
      const sessions = Array.isArray(sessionsData) ? sessionsData : [];

      setDashboard(dashboardData);
      setMessagesPerDay(messages);
      setSessionsPerWeek(sessions);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse">
          <div className="h-28 rounded bg-muted" />
          <div className="h-28 rounded bg-muted" />
          <div className="h-28 rounded bg-muted" />
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {dashboard && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                // Total Sessions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{dashboard.total_sessions}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                // Total Messages
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{dashboard.total_messages}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                // Last Session
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                {dashboard.last_session_at
                  ? new Date(dashboard.last_session_at).toLocaleDateString()
                  : "Never"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {messagesPerDay.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Messages per Day (Last 14 Days)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={messagesPerDay}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#8884d8" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {sessionsPerWeek.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Sessions per Week (Last 8 Weeks)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={sessionsPerWeek}>
                  <XAxis dataKey="week" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
