"use client";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("token", token);
  // Notify listeners (NavBar, pages) that auth state changed
  try {
    window.dispatchEvent(
      new CustomEvent("auth-changed", { detail: { isAuthenticated: true } })
    );
  } catch {}
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  try {
    window.dispatchEvent(
      new CustomEvent("auth-changed", { detail: { isAuthenticated: false } })
    );
  } catch {}
}
