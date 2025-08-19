"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { useRouter } from "next/navigation"
import { apiPost } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"

const RegisterSchema = z.object({
  email: z.string().email("Enter a valid email"),
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .refine((v) => /[A-Z]/.test(v), "Must contain at least one uppercase letter")
    .refine((v) => /[a-z]/.test(v), "Must contain at least one lowercase letter")
    .refine((v) => /\d/.test(v), "Must contain at least one digit"),
})

type RegisterValues = z.infer<typeof RegisterSchema>

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const form = useForm<RegisterValues>({ resolver: zodResolver(RegisterSchema), defaultValues: { email: "", username: "", password: "" } })

  async function onSubmit(values: RegisterValues) {
    try {
      setLoading(true)
      // Minimal payload for backend defaults
      await apiPost("/api/v1/auth/register", {
        email: values.email,
        username: values.username,
        full_name: values.username,
        native_language: "en",
        target_languages: ["ja"],
        current_level: "beginner",
        learning_goals: ["conversation"],
        study_time_preference: 30,
        difficulty_preference: "adaptive",
        preferred_ai_provider: "openai",
        conversation_style: "balanced",
        max_conversation_length: 50,
        auto_save_conversations: true,
        password: values.password,
      })
      // Then login
      const data = await apiPost<{ access_token: string }>("/api/v1/auth/login", { username: values.username, password: values.password })
      if (typeof window !== "undefined") {
        localStorage.setItem("token", data.access_token)
      }
      router.push("/dashboard")
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } }
      const detail = axiosErr?.response?.data?.detail as unknown
      if (Array.isArray(detail) && detail.length > 0) {
        // Show first validation message
        const first = (detail as Array<{ msg?: string }>)[0]
        form.setError("password", { message: String(first?.msg || "Registration failed.") })
      } else if (typeof (detail as string) === "string") {
        form.setError("password", { message: String(detail as string) })
      } else {
        form.setError("password", { message: "Registration failed. Check password rules and unique email/username." })
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-white to-slate-50">
      <div className="w-full max-w-sm bg-white/80 backdrop-blur border rounded-xl p-6 shadow-sm">
        <h1 className="text-2xl font-semibold mb-1">Create your account</h1>
        <p className="text-sm text-muted-foreground mb-6">Start learning Japanese with your AI tutor.</p>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input placeholder="you@example.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input placeholder="yourname" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <Input type="password" placeholder="••••••••" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={loading} className="w-full">{loading ? "Creating..." : "Create account"}</Button>
          </form>
        </Form>
        <p className="text-xs text-muted-foreground mt-4">Already have an account? <a className="underline" href="/login">Sign in</a></p>
      </div>
    </div>
  )
}


