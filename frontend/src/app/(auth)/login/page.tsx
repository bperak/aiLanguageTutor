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

const LoginSchema = z.object({
  username: z.string().min(3, "Username required"),
  password: z.string().min(8, "Password required"),
})

type LoginValues = z.infer<typeof LoginSchema>

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const form = useForm<LoginValues>({ resolver: zodResolver(LoginSchema), defaultValues: { username: "", password: "" } })

  async function onSubmit(values: LoginValues) {
    try {
      setLoading(true)
      const data = await apiPost<{ access_token: string }>("/api/v1/auth/login", values)
      if (typeof window !== "undefined") {
        localStorage.setItem("token", data.access_token)
      }
      router.push("/dashboard")
    } catch {
      form.setError("password", { message: "Login failed. Check credentials." })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-white to-slate-50">
      <div className="w-full max-w-sm bg-white/80 backdrop-blur border rounded-xl p-6 shadow-sm">
        <h1 className="text-2xl font-semibold mb-1">Welcome back</h1>
        {/* Removed dynamic logged_out banner to avoid hydration mismatch */}
        <p className="text-sm text-muted-foreground mb-6">Sign in to continue your learning journey.</p>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" aria-label="Login form">
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
            <Button type="submit" disabled={loading} className="w-full">{loading ? "Signing in..." : "Sign in"}</Button>
          </form>
        </Form>
        <p className="text-xs text-muted-foreground mt-4">Don’t have an account? <a className="underline" href="/register">Create one</a></p>
      </div>
    </div>
  )
}


