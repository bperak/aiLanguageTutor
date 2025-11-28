"use client"

import { useEffect, useState } from "react"
import { apiGet } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"

type CanDoItem = {
  uid: string
  primaryTopic?: string
  primaryTopicEn?: string
  level?: string
  type?: string
  skillDomain?: string
  description?: string
  exampleSentence?: string
  descriptionJa?: string
  titleEn?: string
  titleJa?: string
}

// Helper to convert CEFR levels to numeric
function mapCefrLevelToNumeric(cefrLevel?: string): number {
  const mapping: Record<string, number> = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6
  }
  return mapping[cefrLevel?.toUpperCase() || ""] || 3
}

export default function CanDoPage() {
  const [items, setItems] = useState<CanDoItem[]>([])
  const [q, setQ] = useState("")
  const [level, setLevel] = useState("")
  const [topic, setTopic] = useState("")
  const [levels, setLevels] = useState<string[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [limit, setLimit] = useState(100)
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const [sort, setSort] = useState("level")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchList = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams()
        if (q) params.set("q", q)
        if (level) params.set("level", level)
        if (topic) params.set("topic", topic)
        params.set("limit", String(limit))
        params.set("offset", String(offset))
        params.set("sort", sort)
        const data = await apiGet<{ items: CanDoItem[] }>(`/api/v1/cando/list?${params.toString()}`)
        const itemsToSet = data.items || []
        setItems(itemsToSet)
        // fetch total count separately
        const params2 = new URLSearchParams()
        if (q) params2.set("q", q)
        if (level) params2.set("level", level)
        if (topic) params2.set("topic", topic)
        const count = await apiGet<{ total: number }>(`/api/v1/cando/count?${params2.toString()}`)
        setTotal(count.total || 0)
      } catch (e: any) {
        setError("Failed to load CanDo list")
      } finally {
        setLoading(false)
      }
    }
    fetchList()
    // load dropdown data once
    ;(async () => {
      try {
        const [lv, tp] = await Promise.all([
          apiGet<{ levels: string[] }>("/api/v1/cando/levels"),
          apiGet<{ topics: string[] }>("/api/v1/cando/topics")
        ])
        setLevels(lv.levels || [])
        setTopics(tp.topics || [])
      } catch {
        // ignore filter load errors
      }
    })()
  }, [q, level, topic, limit, offset, sort])

  const filtered = items

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">CanDo Browser</h1>
        <a
          href="/cando/create"
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + Create New CanDo
        </a>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search CanDo or Topic" className="border rounded px-3 py-2" />
        <select value={level} onChange={(e) => { setLevel(e.target.value); setOffset(0) }} className="border rounded px-3 py-2">
          <option value="">All levels</option>
          {levels.map((lv) => (<option key={lv} value={lv}>{lv}</option>))}
        </select>
        <select value={topic} onChange={(e) => { setTopic(e.target.value); setOffset(0) }} className="border rounded px-3 py-2">
          <option value="">All topics</option>
          {topics.map((t) => (<option key={t} value={t}>{t}</option>))}
        </select>
        <button
          onClick={async () => {
            const params = new URLSearchParams()
            if (q) params.set("q", q)
            if (level) params.set("level", level)
            if (topic) params.set("topic", topic)
            params.set("limit", String(limit))
            params.set("offset", String(0))
            params.set("sort", sort)
            setLoading(true)
            setError(null)
            try {
              const data = await apiGet<{ items: CanDoItem[] }>(`/api/v1/cando/list?${params.toString()}`)
              console.log('Search API Response - First item:', data.items?.[0])
              setItems(data.items || [])
              setOffset(0)
              const params2 = new URLSearchParams()
              if (q) params2.set("q", q)
              if (level) params2.set("level", level)
              if (topic) params2.set("topic", topic)
              const count = await apiGet<{ total: number }>(`/api/v1/cando/count?${params2.toString()}`)
              setTotal(count.total || 0)
            } catch {
              setError("Failed to load CanDo list")
            } finally {
              setLoading(false)
            }
          }}
          className="border rounded px-3 py-2 bg-blue-600 text-white"
        >
          Search
        </button>
      </div>
      <div className="flex items-center justify-between mb-4 text-sm text-gray-600">
        <div>{loading ? "Loading..." : error ? error : `Showing ${items.length} of ${total} result(s)`}</div>
        <div className="flex items-center gap-2">
          <label>Sort</label>
          <select value={sort} onChange={(e) => { setSort(e.target.value); setOffset(0) }} className="border rounded px-2 py-1">
            <option value="level">Level</option>
            <option value="topic">Topic</option>
          </select>
          <label>Page size</label>
          <select value={limit} onChange={(e) => { setLimit(parseInt(e.target.value)); setOffset(0) }} className="border rounded px-2 py-1">
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
          <button disabled={offset===0} onClick={() => setOffset(Math.max(0, offset - limit))} className="border rounded px-2 py-1">Prev</button>
          <button disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)} className="border rounded px-2 py-1">Next</button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((it) => {
          // Check if we have actual AI-generated titles
          const hasTitleEn = it.titleEn && typeof it.titleEn === 'string' && it.titleEn.trim().length > 0
          const hasTitleJa = it.titleJa && typeof it.titleJa === 'string' && it.titleJa.trim().length > 0
          const hasActualTitle = hasTitleEn || hasTitleJa
          
          // Topic/category info (always available)
          const topicJa = it.primaryTopic && typeof it.primaryTopic === 'string' ? it.primaryTopic.trim() : null
          const topicEn = it.primaryTopicEn && typeof it.primaryTopicEn === 'string' ? it.primaryTopicEn.trim() : null
          
          // Use actual titles if available, otherwise use topic as title
          const displayTitleEn = hasTitleEn 
            ? it.titleEn.trim() 
            : (topicEn || it.uid)
          
          const displayTitleJa = hasTitleJa
            ? it.titleJa.trim()
            : (topicJa || null)
          
          return (
            <Card key={it.uid} className="flex flex-col h-full hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                {/* Level & Type Badges */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Level {it.level || "N/A"}
                  </span>
                  {it.type && (
                    <span className="text-xs text-gray-500 uppercase">{it.type}</span>
                  )}
                </div>
                
                {/* Title - Full bilingual titles, no truncation - ALWAYS show title */}
                <CardTitle className="text-base md:text-lg">
                  {displayTitleJa ? (
                    <>
                      <div className="font-semibold mb-0.5">{displayTitleJa}</div>
                      {displayTitleEn && displayTitleEn !== displayTitleJa && (
                        <div className="text-sm font-normal text-gray-600">
                          {displayTitleEn}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="font-semibold">{displayTitleEn}</div>
                  )}
                </CardTitle>
              </CardHeader>
              
              <CardContent className="flex-grow flex flex-col pt-0">
                {/* Topic/Category Badge - Always show category/topic */}
                {(topicJa || topicEn) && (
                  <div className="mb-1.5">
                    <div className="flex flex-wrap gap-1">
                      {topicJa && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded font-medium">
                          {topicJa}
                        </span>
                      )}
                      {topicEn && topicEn !== topicJa && (
                        <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded border border-green-200">
                          {topicEn}
                        </span>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Skill Domain */}
                {it.skillDomain && (
                  <div>
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                      {it.skillDomain}
                    </span>
                  </div>
                )}
              </CardContent>
              
              {/* Actions - pushed to bottom */}
              <CardFooter className="pt-2 border-t flex gap-2">
                <a 
                  href={`/cando/${encodeURIComponent(it.uid)}?level=${mapCefrLevelToNumeric(it.level)}`} 
                  className="flex-1 text-center px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs md:text-sm font-medium hover:bg-blue-700 transition-colors active:bg-blue-800"
                >
                  Start Lesson
                </a>
                <a 
                  href={`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/cando/lessons/package?can_do_id=${encodeURIComponent(it.uid)}`} 
                  target="_blank" 
                  rel="noreferrer" 
                  className="px-3 py-1.5 border border-gray-300 rounded-md text-xs md:text-sm text-gray-700 hover:bg-gray-50 transition-colors active:bg-gray-100"
                >
                  Data
                </a>
              </CardFooter>
            </Card>
          )
        })}
      </div>
    </div>
  )
}


