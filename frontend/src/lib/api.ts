"use client"

import axios, { type AxiosRequestConfig } from "axios"

const BASE_URL =
  typeof window !== "undefined"
    ? ""
    : process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

function isPublicGetPath(path: string): boolean {
  return (
    path.startsWith("/api/v1/ai-content/word/") ||
    path.startsWith("/api/v1/ai-content/status/") ||
    path.startsWith("/api/v1/health")
  )
}

function resolveToken(token?: string): string | undefined {
  if (token) return token
  if (typeof window === "undefined") return undefined
  return localStorage.getItem("token") ?? undefined
}

export async function apiGet<T>(path: string, token?: string, config?: AxiosRequestConfig) {
  const headers: Record<string, string> = {
    Accept: "application/json; charset=utf-8",
  }
  const attachAuth = !isPublicGetPath(path)
  const authToken = attachAuth ? resolveToken(token) : undefined
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  // Reason: Lexical graph queries can be slow, so use longer timeout for graph endpoints
  // Default timeout for other endpoints is 30s, graph endpoints get 60s
  const defaultTimeout = path.includes("/lexical/graph") ? 60000 : 30000

  const resp = await axios.get<T>(`${BASE_URL}${path}`, {
    ...(config || {}),
    headers: { ...(config?.headers || {}), ...headers },
    responseType: "json",
    responseEncoding: "utf8",
    validateStatus: (status) => status < 500,
    timeout: config?.timeout ?? defaultTimeout,
  })
  return resp.data
}

export async function apiPost<T>(
  path: string,
  data?: unknown,
  token?: string,
  config?: AxiosRequestConfig
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  const authToken = resolveToken(token)
  if (authToken) headers.Authorization = `Bearer ${authToken}`
  const resp = await axios.post<T>(`${BASE_URL}${path}`, data ?? {}, {
    ...(config || {}),
    headers: { ...(config?.headers || {}), ...headers },
    timeout: config?.timeout ?? 10000,
  })
  return resp.data
}

export async function apiPut<T>(
  path: string,
  data?: unknown,
  token?: string,
  config?: AxiosRequestConfig
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  const authToken = resolveToken(token)
  if (authToken) headers.Authorization = `Bearer ${authToken}`
  const resp = await axios.put<T>(`${BASE_URL}${path}`, data ?? {}, {
    ...(config || {}),
    headers: { ...(config?.headers || {}), ...headers },
  })
  return resp.data
}

export async function apiDelete<T>(path: string, token?: string, config?: AxiosRequestConfig) {
  const headers: Record<string, string> = {}
  const authToken = resolveToken(token)
  if (authToken) headers.Authorization = `Bearer ${authToken}`
  const resp = await axios.delete<T>(`${BASE_URL}${path}`, {
    ...(config || {}),
    headers: { ...(config?.headers || {}), ...headers },
  })
  return resp.data
}

export async function createCanDo(descriptionEn?: string, descriptionJa?: string) {
  // Reason: CanDo creation involves AI operations (translation, title generation, field inference),
  // embedding generation, and similarity relationship creation, which can take longer than 10s
  return apiPost<{ success?: boolean; canDo?: any }>(
    "/api/v1/cando/create",
    {
      descriptionEn,
      descriptionJa,
    },
    undefined,
    { timeout: 60000 } // 60 seconds timeout for CanDo creation
  )
}

export async function getLessonGenerationStatus(lessonId: number, version?: number) {
  const query = new URLSearchParams({ lesson_id: String(lessonId) })
  if (version !== undefined) query.set("version", String(version))
  return apiGet(`/api/v1/cando/lessons/generation-status?${query.toString()}`)
}

export async function regenerateLessonStage(
  lessonId: number,
  version: number,
  stage: "comprehension" | "production" | "interaction",
  userId?: string
) {
  const query = new URLSearchParams({
    lesson_id: String(lessonId),
    version: String(version),
    stage,
  })
  if (userId) query.set("user_id", userId)
  return apiPost(`/api/v1/cando/lessons/regenerate-stage?${query.toString()}`, {})
}

type CompileStatusHandler = (payload: any) => void

export async function compileLessonV2Stream(
  canDoId: string,
  metalanguage: string = "en",
  model: string = "gpt-4.1",
  onStatus?: CompileStatusHandler,
  userId?: string | null,
  fastModel?: string | null,
  incremental: boolean = true,
  signal?: AbortSignal
): Promise<any> {
  const params = new URLSearchParams({
    can_do_id: canDoId,
    metalanguage,
    model,
  })
  if (userId) params.set("user_id", userId)
  if (fastModel) params.set("fast_model", fastModel)
  if (incremental) params.set("incremental", "true")

  const token = resolveToken()
  const resp = await fetch(`${BASE_URL}/api/v1/cando/lessons/compile_v2_stream?${params}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    signal, // Add AbortSignal support
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`Stream error: ${resp.status}`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let lastPayload: any = null

  while (true) {
    // Check if request was aborted
    if (signal?.aborted) {
      reader.cancel()
      throw new Error("Request cancelled")
    }
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const lines = chunk.split("\n")
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        // Handle error events
        if (line.startsWith("event: error")) {
          const nextLine = lines[i + 1]
          if (nextLine && nextLine.startsWith("data: ")) {
            const errorData = nextLine.slice(6)
            try {
              const errorPayload = JSON.parse(errorData)
              throw new Error(errorPayload.detail || errorPayload.error || "Compilation failed")
            } catch (parseErr) {
              if (parseErr instanceof Error && parseErr.message !== "Unexpected end of JSON input") {
                throw parseErr
              }
              throw new Error(errorData || "Compilation failed")
            }
          }
          throw new Error("Compilation failed")
        }
        // Handle data events
        if (line.startsWith("data: ")) {
          const data = line.slice(6)
          if (!data || data === "[DONE]") continue
          try {
            const payload = JSON.parse(data)
            // Check if payload indicates an error
            if (payload.status === "error" || payload.error) {
              throw new Error(payload.detail || payload.error || "Compilation failed")
            }
            lastPayload = payload
            if (onStatus) onStatus(payload)
          } catch (parseErr) {
            // If JSON parse failed, might be an error message
            if (parseErr instanceof Error && parseErr.message !== "Unexpected end of JSON input") {
              throw parseErr
            }
            // ignore non-JSON data lines
          }
        }
      }
    }
  }

  return lastPayload
}

// Simple non-streaming version for backward compatibility
export async function compileLessonV2(
  canDoId: string,
  metalanguage: string = "en",
  model: string = "gpt-4o"
): Promise<any> {
  return compileLessonV2Stream(canDoId, metalanguage, model)
}
