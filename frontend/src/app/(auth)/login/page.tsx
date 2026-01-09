"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { apiPost } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const LoginSchema = z.object({
  username: z.string().min(1, "Username is required").min(3, "Username must be at least 3 characters"),
  password: z.string().min(1, "Password is required").min(8, "Password must be at least 8 characters"),
});

type LoginValues = z.infer<typeof LoginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const form = useForm<LoginValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { username: "", password: "" },
    mode: "onBlur", // Validate on blur to avoid premature validation
    reValidateMode: "onChange", // Re-validate on change after first blur
  });

  async function onSubmit(values: LoginValues) {
    // Immediately disable button for instant feedback (before React re-render)
    const submitButton = document.querySelector(
      'button[type="submit"]'
    ) as HTMLButtonElement;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Signing in...";
    }

    try {
      setLoading(true);
      const data = await apiPost<{ access_token: string }>(
        "/api/v1/auth/login",
        values
      );

      if (typeof window !== "undefined") {
        setToken(data.access_token);
      }

      router.push("/");
    } catch (error: any) {
      // Log full error details for debugging
      console.error("Login error:", {
        error,
        message: error?.message,
        response: error?.response,
        status: error?.response?.status,
        data: error?.response?.data,
        stack: error?.stack
      });
      
      // Extract error message from various possible locations
      const errorMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        (error?.response?.status === 500 
          ? "Server error. Please try again later." 
          : "Login failed. Check credentials.");
      form.setError("password", { message: errorMessage });

      // Re-enable button on error
      const submitButton = document.querySelector(
        'button[type="submit"]'
      ) as HTMLButtonElement;
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = "Sign in";
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-background to-muted">
      <div className="w-full max-w-sm bg-card/80 backdrop-blur border border-border rounded-xl p-6 shadow-sm">
        <h1 className="text-2xl font-semibold mb-1">Welcome back</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Sign in to continue your learning journey.
        </p>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-4"
            aria-label="Login form"
          >
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="yourname" 
                      {...field}
                      value={field.value || ""}
                      autoComplete="username"
                      onChange={(e) => {
                        const value = e.target.value;
                        field.onChange(value);
                        // Clear any previous errors when user starts typing
                        if (form.formState.errors.username) {
                          form.clearErrors("username");
                        }
                      }}
                      onBlur={field.onBlur}
                    />
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
                    <Input 
                      type="password" 
                      placeholder="••••••••" 
                      {...field}
                      value={field.value || ""}
                      autoComplete="current-password"
                      onChange={(e) => {
                        const value = e.target.value;
                        field.onChange(value);
                        // Clear any previous errors when user starts typing
                        if (form.formState.errors.password) {
                          form.clearErrors("password");
                        }
                      }}
                      onBlur={field.onBlur}
                      onKeyDown={(e) => {
                        // Allow Enter key to submit form
                        if (e.key === "Enter" && !loading) {
                          e.preventDefault();
                          form.handleSubmit(onSubmit)();
                        }
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </Form>
        <p className="text-xs text-muted-foreground mt-4">
          Don&apos;t have an account?{" "}
          <a className="underline" href="/register">
            Create one
          </a>
        </p>
      </div>
    </div>
  );
}
