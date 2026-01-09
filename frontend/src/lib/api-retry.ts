"use client";

import { AxiosError } from "axios";

export interface RetryConfig {
  maxRetries?: number;
  retryDelay?: number | ((attempt: number) => number);
  retryCondition?: (error: AxiosError) => boolean;
  onRetry?: (attempt: number, error: AxiosError) => void;
}

const defaultRetryCondition = (error: AxiosError): boolean => {
  // Retry on network errors or 5xx server errors
  if (!error.response) {
    return true; // Network error
  }
  const status = error.response.status;
  return status >= 500 && status < 600;
};

const defaultRetryDelay = (attempt: number): number => {
  // Exponential backoff: 1s, 2s, 4s, etc.
  return Math.min(1000 * Math.pow(2, attempt), 10000);
};

export async function apiCallWithRetry<T>(
  apiCall: () => Promise<T>,
  config: RetryConfig = {}
): Promise<T> {
  const {
    maxRetries = 3,
    retryDelay = defaultRetryDelay,
    retryCondition = defaultRetryCondition,
    onRetry,
  } = config;

  let lastError: AxiosError | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await apiCall();
    } catch (error) {
      lastError = error as AxiosError;

      // Don't retry if it's the last attempt or condition doesn't match
      if (attempt >= maxRetries || !retryCondition(lastError)) {
        throw lastError;
      }

      // Call onRetry callback if provided
      if (onRetry) {
        onRetry(attempt + 1, lastError);
      }

      // Wait before retrying
      const delay =
        typeof retryDelay === "function" ? retryDelay(attempt) : retryDelay;
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}
