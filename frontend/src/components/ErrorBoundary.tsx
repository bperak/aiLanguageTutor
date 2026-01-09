"use client";

import { useEffect } from "react";

/**
 * Suppresses browser extension errors that don't affect app functionality.
 * 
 * Reason: Browser extensions (ad blockers, password managers, etc.) can cause
 * "message channel closed" errors that are harmless but clutter the console.
 */
export function ErrorBoundary({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Suppress browser extension message channel errors
    const originalError = window.console.error;
    window.console.error = (...args: any[]) => {
      const message = args[0]?.toString() || "";
      // Filter out known browser extension errors
      if (
        message.includes("message channel closed") ||
        message.includes("Extension context invalidated") ||
        message.includes("A listener indicated an asynchronous response")
      ) {
        // Silently ignore these errors
        return;
      }
      // Log other errors normally
      originalError.apply(console, args);
    };

    // Also handle unhandled promise rejections from extensions
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason?.toString() || "";
      if (
        reason.includes("message channel closed") ||
        reason.includes("Extension context invalidated") ||
        reason.includes("A listener indicated an asynchronous response")
      ) {
        event.preventDefault();
        return;
      }
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.console.error = originalError;
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  return <>{children}</>;
}
