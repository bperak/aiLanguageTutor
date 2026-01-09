import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats a session name based on creation date.
 * Returns "Today" for today, "Yesterday" for yesterday, or formatted date for older sessions.
 *
 * @param createdAt - ISO date string or Date object
 * @returns Formatted session name
 */
export function formatSessionName(createdAt: string | Date | undefined): string {
  if (!createdAt) return "Session";
  
  const date = typeof createdAt === "string" ? new Date(createdAt) : createdAt;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const sessionDate = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate()
  );
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (sessionDate.getTime() === today.getTime()) {
    return "Today";
  } else if (sessionDate.getTime() === yesterday.getTime()) {
    return "Yesterday";
  } else {
    // Format as "Nov 6, 2024"
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }
}

/**
 * Cleans up session title by removing "Home:" prefix if present.
 *
 * @param title - Original session title
 * @returns Cleaned title
 */
export function cleanSessionTitle(title: string | undefined | null): string {
  if (!title) return "Session";
  return title.replace(/^Home:\s*/i, "").trim() || "Session";
}
