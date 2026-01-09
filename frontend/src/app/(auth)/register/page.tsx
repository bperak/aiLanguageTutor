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
import { Check, X, AlertCircle } from "lucide-react";

const RegisterSchema = z.object({
  email: z.string().email("Enter a valid email"),
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .refine((v) => /[A-Z]/.test(v), "Must contain at least one uppercase letter")
    .refine((v) => /[a-z]/.test(v), "Must contain at least one lowercase letter")
    .refine((v) => /\d/.test(v), "Must contain at least one digit"),
});

type RegisterValues = z.infer<typeof RegisterSchema>;

/**
 * Password requirements indicator component.
 * Shows real-time feedback on password strength as user types.
 */
function PasswordRequirements({ password }: { password: string }) {
  const requirements = [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One digit", met: /\d/.test(password) },
  ];

  return (
    <div className="mt-2 space-y-1">
      {requirements.map((req, idx) => (
        <div key={idx} className="flex items-center gap-2 text-xs">
          {req.met ? (
            <Check className="h-3.5 w-3.5 text-green-600" />
          ) : (
            <X className="h-3.5 w-3.5 text-muted-foreground" />
          )}
          <span
            className={
              req.met
                ? "text-green-700 dark:text-green-400"
                : "text-muted-foreground"
            }
          >
            {req.label}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * Form-level error banner component.
 * Displays unexpected/general errors at the top of the form.
 */
function FormErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-2">
      <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
      <p className="text-sm text-red-700">{message}</p>
    </div>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<RegisterValues>({
    resolver: zodResolver(RegisterSchema),
    defaultValues: { email: "", username: "", password: "" },
    mode: "onChange", // Enable real-time validation
  });

  // Watch password for real-time requirements display
  const passwordValue = form.watch("password");

  async function onSubmit(values: RegisterValues) {
    // Immediately disable button for instant feedback (before React re-render)
    const submitButton = document.querySelector(
      'button[type="submit"]'
    ) as HTMLButtonElement;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Creating...";
    }

    try {
      setLoading(true);
      setFormError(null);

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
      });

      // Then login
      const data = await apiPost<{ access_token: string }>(
        "/api/v1/auth/login",
        {
          username: values.username,
          password: values.password,
        }
      );

      if (typeof window !== "undefined") {
        setToken(data.access_token);
      }

      // Redirect to home page (which will show chat interface or redirect to profile build if needed)
      router.push("/");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr?.response?.data?.detail;

      // Route errors to the correct field based on backend response
      if (Array.isArray(detail) && detail.length > 0) {
        // Handle Pydantic validation errors (array format)
        const first = (detail as Array<{ msg?: string; loc?: string[] }>)[0];
        const message = String(first?.msg || "Validation error");
        const location = first?.loc?.join(".") || "";

        if (location.includes("email")) {
          form.setError("email", { message });
        } else if (location.includes("username")) {
          form.setError("username", { message });
        } else if (location.includes("password")) {
          form.setError("password", { message });
        } else {
          setFormError(message);
        }
      } else if (typeof detail === "string") {
        // Handle string error messages from backend
        const detailLower = detail.toLowerCase();

        if (detailLower.includes("username") && detailLower.includes("registered")) {
          form.setError("username", {
            message: "This username is already taken. Please choose another.",
          });
        } else if (detailLower.includes("email") && detailLower.includes("registered")) {
          form.setError("email", {
            message: "This email is already registered. Try signing in instead.",
          });
        } else if (detailLower.includes("password")) {
          form.setError("password", { message: detail });
        } else {
          // Show as form-level error if we can't categorize it
          setFormError(detail);
        }
      } else {
        // Fallback for unknown error format
        setFormError(
          "Registration failed. Please try again or contact support if the issue persists."
        );
      }

      // Re-enable button on error
      const submitButton = document.querySelector(
        'button[type="submit"]'
      ) as HTMLButtonElement;
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = "Create account";
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-background to-muted">
      <div className="w-full max-w-sm bg-card/80 backdrop-blur border border-border rounded-xl p-6 shadow-sm">
        <h1 className="text-2xl font-semibold mb-1">Create your account</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Start learning Japanese with your AI tutor.
        </p>
        <FormErrorBanner message={formError} />
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
                  <PasswordRequirements password={passwordValue || ""} />
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Creating..." : "Create account"}
            </Button>
          </form>
        </Form>
        <p className="text-xs text-muted-foreground mt-4">
          Already have an account?{" "}
          <a className="underline" href="/login">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
