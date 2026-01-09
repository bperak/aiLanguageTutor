"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api";
import { getToken } from "@/lib/auth";
import HomeChatInterface from "@/components/home/HomeChatInterface";

// Landing page component - shown by default
function LandingPage() {
  return (
    <div className="min-h-[calc(100vh-56px)] grid place-items-center p-8">
      <div className="text-center max-w-xl">
        <h1 className="text-4xl font-semibold tracking-tight">
          Learn languages with your AI tutor
        </h1>
        <p className="text-muted-foreground mt-3">
          Personalized, simple, and effective. Start with Japanese today.
        </p>
        <div className="mt-6 flex items-center justify-center gap-4">
          <a
            className="px-5 py-2 rounded-md bg-foreground text-background hover:opacity-90"
            href="/register"
          >
            Get started
          </a>
          <a
            className="px-5 py-2 rounded-md border border-border hover:bg-accent"
            href="/login"
          >
            I already have an account
          </a>
        </div>
      </div>
    </div>
  );
}

// Loading spinner component
function LoadingSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const [authState, setAuthState] = useState<
    "checking" | "authenticated" | "unauthenticated"
  >("checking");
  const [profileStatus, setProfileStatus] = useState<{
    profile_completed: boolean;
    profile_skipped: boolean;
  } | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      // Check for token on client side only
      if (typeof window === "undefined") {
        return;
      }

      const token = getToken();
      if (!token) {
        setAuthState("unauthenticated");
        return;
      }

      try {
        const status = await apiGet<{
          profile_completed: boolean;
          profile_skipped: boolean;
        }>("/api/v1/profile/status");

        setProfileStatus(status);

        if (!status.profile_completed && !status.profile_skipped) {
          router.push("/profile/build");
          return;
        }

        setAuthState("authenticated");
      } catch {
        setAuthState("unauthenticated");
      }
    };

    checkAuth();
  }, [router]);

  // Show landing page immediately for unauthenticated users (no API call needed)
  if (authState === "unauthenticated") {
    return <LandingPage />;
  }

  // Show landing page while checking auth (better UX than spinner)
  if (authState === "checking") {
    return <LandingPage />;
  }

  // Show loading only when we know user is authenticated but still loading profile
  if (authState === "authenticated" && !profileStatus) {
    return <LoadingSpinner />;
  }

  // Main chat interface for authenticated users
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      <HomeChatInterface profileStatus={profileStatus} />
    </div>
  );
}
