import { useCallback } from "react";
import { useToast } from "@/components/ToastProvider";
import { logError } from "@/lib/constants";

/**
 * Custom hook for standardized error handling
 */
export function useErrorHandler() {
  const { showToast } = useToast();

  const handleError = useCallback(
    (
      error: unknown,
      options?: {
        showToast?: boolean;
        toastMessage?: string;
        logPrefix?: string;
      }
    ) => {
      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === "string"
          ? error
          : "An unexpected error occurred";

      // Log error
      if (options?.logPrefix) {
        logError(`${options.logPrefix}:`, error);
      } else {
        logError("Error:", error);
      }

      // Show toast if requested
      if (options?.showToast !== false) {
        showToast(
          options?.toastMessage || `❌ ${errorMessage}`
        );
      }

      return errorMessage;
    },
    [showToast]
  );

  return { handleError };
}
