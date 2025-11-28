import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Remove standalone output for development - it's only needed for production
  // output: 'standalone',
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
};

export default nextConfig;
