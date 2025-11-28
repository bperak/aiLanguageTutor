import type { Metadata } from "next";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { ToastProvider } from "@/components/ToastProvider";
import { DisplaySettingsProvider } from "@/contexts/DisplaySettingsContext";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Language Tutor",
  description: "Learn languages with an AI-powered tutor",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased font-sans min-h-screen bg-background text-foreground`}>
        <DisplaySettingsProvider>
          <ToastProvider>
            <a href="#main-content" className="skip-link">Skip to content</a>
            <NavBar />
            <main id="main-content" tabIndex={-1}>
              {children}
            </main>
          </ToastProvider>
        </DisplaySettingsProvider>
      </body>
    </html>
  );
}
