/**
 * Utility functions for localStorage operations
 */

/**
 * Sanitizes a key for use in localStorage to prevent collisions
 * @param key - The key to sanitize
 * @returns A sanitized key safe for localStorage
 */
export function sanitizeStorageKey(key: string): string {
  // Encode special characters and limit length
  const sanitized = encodeURIComponent(key)
    .replace(/[^a-zA-Z0-9\-_.]/g, "_")
    .substring(0, 200); // Limit length to prevent issues
  return `lesson_status_${sanitized}`;
}

/**
 * Gets an item from localStorage with a sanitized key
 * @param canDoId - The CanDo ID to use as part of the key
 * @returns The stored value or null
 */
export function getStorageItem(canDoId: string): string | null {
  if (typeof window === "undefined") return null;
  const key = sanitizeStorageKey(canDoId);
  return localStorage.getItem(key);
}

/**
 * Sets an item in localStorage with a sanitized key
 * @param canDoId - The CanDo ID to use as part of the key
 * @param value - The value to store
 */
export function setStorageItem(canDoId: string, value: string): void {
  if (typeof window === "undefined") return;
  const key = sanitizeStorageKey(canDoId);
  localStorage.setItem(key, value);
}
