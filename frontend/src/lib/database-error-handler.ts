/**
 * Database error handling utilities
 * Handles database-specific HTTP errors with user-friendly messages
 */

export interface DatabaseError {
  status: number;
  message: string;
  retryable: boolean;
  shouldRefresh?: boolean;
}

/**
 * Handles database-specific errors and returns user-friendly messages
 * @param error - The error object from axios/fetch
 * @returns DatabaseError with status, message, and retryable flag
 */
export function handleDatabaseError(error: any): DatabaseError {
  const status = error?.response?.status || error?.status || 500;
  const detail = error?.response?.data?.detail || error?.message || "An unknown error occurred";

  // Database connection pool exhausted
  if (status === 503) {
    return {
      status,
      message: "Database temporarily unavailable. Please try again in a moment.",
      retryable: true,
    };
  }

  // Concurrent update conflict
  if (status === 409) {
    return {
      status,
      message: "Lesson was updated by another process. Refreshing...",
      retryable: true,
      shouldRefresh: true,
    };
  }

  // Gateway timeout (long-running queries)
  if (status === 504) {
    return {
      status,
      message: "Request timed out. The lesson may be very large. Please try again.",
      retryable: true,
    };
  }

  // Bad request (validation errors)
  if (status === 400) {
    return {
      status,
      message: detail || "Invalid request. Please check your input.",
      retryable: false,
    };
  }

  // Not found
  if (status === 404) {
    return {
      status,
      message: detail || "Resource not found.",
      retryable: false,
    };
  }

  // Generic server error
  if (status >= 500) {
    return {
      status,
      message: detail || "Server error. Please try again later.",
      retryable: true,
    };
  }

  // Default case
  return {
    status,
    message: detail || "An error occurred.",
    retryable: false,
  };
}

/**
 * Checks if an error is a database-related error
 */
export function isDatabaseError(error: any): boolean {
  const status = error?.response?.status || error?.status;
  return status === 503 || status === 409 || status === 504 || (status >= 500 && status < 600);
}
