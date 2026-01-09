import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "ai-language-tutor-frontend",
    version: "0.1.0",
    timestamp: new Date().toISOString(),
  });
}
