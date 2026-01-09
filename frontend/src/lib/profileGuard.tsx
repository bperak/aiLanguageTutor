"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api";
import { getToken } from "@/lib/auth";

interface ProfileGuardProps {
  children: React.ReactNode;
  requireCompleted?: boolean;
}

/**
 * Profile completion guard component.
 * Redirects to profile building if profile is not completed (when requireCompleted is true).
 * For flexible access, this is optional and can be used selectively.
 */
export function ProfileGuard({
  children,
  requireCompleted = false,
}: ProfileGuardProps) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    if (!requireCompleted) {
      // If not requiring completion, allow access
      setAllowed(true);
      setChecking(false);
      return;
    }

    // Check profile status
    apiGet<{ profile_completed: boolean; profile_skipped: boolean }>(
      "/api/v1/profile/status"
    )
      .then((status) => {
        if (status.profile_completed || status.profile_skipped) {
          setAllowed(true);
        } else {
          // Redirect to profile building
          router.replace("/profile/build");
        }
        setChecking(false);
      })
      .catch(() => {
        // On error, allow access (don't block)
        setAllowed(true);
        setChecking(false);
      });
  }, [router, requireCompleted]);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!allowed) {
    return null;
  }

  return <>{children}</>;
}
