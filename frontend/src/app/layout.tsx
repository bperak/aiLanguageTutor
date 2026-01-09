import type { Metadata } from "next";
import NavBar from "@/components/NavBar";
import { ToastProvider } from "@/components/ToastProvider";
import { DisplaySettingsProvider } from "@/contexts/DisplaySettingsContext";
import { ConnectionStatus } from "@/components/ui/connection-status";
import { ErrorBoundary } from "@/components/ErrorBoundary";
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
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var saved=localStorage.getItem("theme");var prefers=window.matchMedia("(prefers-color-scheme: dark)").matches;var theme=saved|| (prefers?"dark":"light");document.documentElement.classList.toggle("dark",theme==="dark");}catch(e){}})();`,
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased font-sans min-h-screen bg-background text-foreground`}
        suppressHydrationWarning
      >
        <ErrorBoundary>
          <DisplaySettingsProvider>
            <ToastProvider>
              <a
                href="#main-content"
                className="skip-link"
              >
                Skip to content
              </a>
              <NavBar />
              <main id="main-content" tabIndex={-1} suppressHydrationWarning>
                {children}
              </main>
              <ConnectionStatus />
            </ToastProvider>
          </DisplaySettingsProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
