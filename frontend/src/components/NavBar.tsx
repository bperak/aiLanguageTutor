import Link from "next/link"
import ThemeToggle from "./ThemeToggle"

export default function NavBar() {
  return (
    <nav className="w-full border-b bg-white/70 backdrop-blur sticky top-0 z-10" role="navigation" aria-label="Main">
      <div className="max-w-5xl mx-auto flex items-center justify-between p-3 sm:p-4">
        <Link className="font-semibold focus:outline-none focus:ring-2 focus:ring-ring rounded" href="/">AI Language Tutor</Link>
        <div className="hidden sm:flex space-x-4 text-sm items-center">
          <Link className="hover:underline" href="/login">Login</Link>
          <Link className="hover:underline" href="/register">Sign up</Link>
          <Link className="hover:underline" href="/dashboard">Dashboard</Link>
          <Link className="hover:underline" href="/conversations">Conversations</Link>
          <Link className="hover:underline" href="/content/analyze">Analyze</Link>
          <Link className="hover:underline" href="/knowledge">Knowledge</Link>
          <Link className="hover:underline" href="/grammar">Grammar</Link>
          <Link className="hover:underline" href="/srs">SRS</Link>
          <Link className="hover:underline" href="/profile">Profile</Link>
          <Link className="hover:underline" href="/logout">Logout</Link>
          <ThemeToggle />
        </div>
        <div className="sm:hidden">
          <ThemeToggle />
        </div>
      </div>
    </nav>
  )
}


