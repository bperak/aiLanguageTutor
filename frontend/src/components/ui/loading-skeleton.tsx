"use client";

import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular" | "rounded";
  width?: string | number;
  height?: string | number;
  animation?: "pulse" | "wave" | "none";
}

export function LoadingSkeleton({
  className,
  variant = "rectangular",
  width,
  height,
  animation = "pulse",
}: LoadingSkeletonProps) {
  const baseStyles = "bg-muted";
  const variantStyles = {
    text: "h-4 rounded",
    circular: "rounded-full",
    rectangular: "",
    rounded: "rounded-md",
  };
  const animationStyles = {
    pulse: "animate-pulse",
    wave: "animate-[wave_1.6s_ease-in-out_0.5s_infinite]",
    none: "",
  };

  return (
    <div
      className={cn(
        baseStyles,
        variantStyles[variant],
        animationStyles[animation],
        className
      )}
      style={{
        width: width || (variant === "circular" ? height || "40px" : "100%"),
        height: height || (variant === "circular" ? width || "40px" : "1rem"),
      }}
      aria-busy="true"
      aria-label="Loading"
    />
  );
}

// Pre-built skeleton components for common use cases
export function ChatMessageSkeleton() {
  return (
    <div className="flex gap-3 p-4">
      <LoadingSkeleton variant="circular" width={40} height={40} />
      <div className="flex-1 space-y-2">
        <LoadingSkeleton variant="text" width="60%" />
        <LoadingSkeleton variant="text" width="80%" />
        <LoadingSkeleton variant="text" width="40%" />
      </div>
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="space-y-4 p-6 border rounded-lg">
      <LoadingSkeleton variant="text" width="40%" height={24} />
      <LoadingSkeleton variant="text" width="100%" />
      <LoadingSkeleton variant="text" width="100%" />
      <LoadingSkeleton variant="text" width="60%" />
    </div>
  );
}

export function InputSkeleton() {
  return (
    <div className="space-y-2">
      <LoadingSkeleton variant="text" width="30%" height={16} />
      <LoadingSkeleton variant="rounded" width="100%" height={40} />
    </div>
  );
}
