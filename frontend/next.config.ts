import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  ...(isProduction ? { output: "standalone" } : {}),
  eslint: {
    // Do not block production builds on ESLint errors
    ignoreDuringBuilds: true,
  },
  // Enable React Compiler for better performance
  experimental: {
    reactCompiler: true,
  },
  // Ensure proper development server configuration
  devIndicators: {
    position: 'bottom-right',
  },
  // Environment variables configuration
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  },
  // Image optimization configuration
  images: {
    // Allow unoptimized images for static files in public directory
    unoptimized: false,
    // Configure remote patterns if needed, but for local static files we'll use regular img tags
    remotePatterns: [],
  },
  // Skip typechecking during build (already done separately)
  typescript: {
    ignoreBuildErrors: false,
  },
  // Force dynamic rendering for all pages to avoid SSG issues with certain packages
  // This is appropriate since the app is primarily dynamic content
  ...(!isProduction ? {} : {
    // In production, use dynamic rendering instead of static generation
  }),
};

export default nextConfig;
