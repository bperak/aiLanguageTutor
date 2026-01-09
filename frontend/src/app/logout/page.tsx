"use client";
import { useEffect } from "react";
import { clearToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
export default function LogoutPage() {
  const router = useRouter();
  useEffect(() => {
    clearToken();
    // router.replace("/login?logged_out=1");
  }, [router]);
  return (
    <div className="min-h-[calc(100vh-56px)] grid place-items-center p-8">
      <div className="text-center max-w-md">
        <p className="text-sm text-muted-foreground">Signing you out...</p>
      </div>
    </div>
  );
}
