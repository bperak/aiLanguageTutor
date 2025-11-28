"use client"

import Link from "next/link"
import { useState, useEffect } from "react"
import ThemeToggle from "./ThemeToggle"
import { ChevronDown, Menu, X } from "lucide-react"
import { getToken } from "@/lib/auth"

interface DropdownItem {
  label: string
  href: string
  description?: string
}

interface DropdownProps {
  label: string
  items: DropdownItem[]
  isOpen: boolean
  onToggle: () => void
}

function Dropdown({ label, items, isOpen, onToggle }: DropdownProps) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {label}
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-[90]">
          <div className="py-1">
            {items.map((item, index) => (
              <Link
                key={index}
                href={item.href}
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 transition-colors"
                onClick={() => onToggle()}
              >
                <div className="font-medium">{item.label}</div>
                {item.description && (
                  <div className="text-xs text-gray-500 mt-0.5">{item.description}</div>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function NavBar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  const handleDropdownToggle = (dropdown: string) => {
    setActiveDropdown(activeDropdown === dropdown ? null : dropdown)
  }

  const closeAllDropdowns = () => {
    setActiveDropdown(null)
    setIsMobileMenuOpen(false)
  }

  // Check authentication status and react to changes
  useEffect(() => {
    const refresh = () => setIsAuthenticated(!!getToken())
    refresh()
    // Listen for our custom event and cross-tab storage updates
    window.addEventListener("auth-changed", refresh as EventListener)
    window.addEventListener("storage", (e) => {
      if (e.key === "token") refresh()
    })
    return () => {
      window.removeEventListener("auth-changed", refresh as EventListener)
    }
  }, [])

  const lexicalItems: DropdownItem[] = [
    { label: "Lexical Graph", href: "/lexical/graph", description: "Interactive word network visualization" },
    { label: "Lexical Lessons", href: "/lexical/lessons", description: "Structured vocabulary learning" },
    { label: "Knowledge Base", href: "/knowledge", description: "Content analysis and insights" }
  ]

  const grammarItems: DropdownItem[] = [
    { label: "Grammar Study", href: "/grammar", description: "Grammar patterns and rules" },
    { label: "Grammar Patterns", href: "/grammar/study", description: "Interactive grammar exercises" },
    { label: "SRS System", href: "/srs", description: "Spaced repetition learning" }
  ]

  const profileItems: DropdownItem[] = [
    { label: "Profile Settings", href: "/profile", description: "Account and preferences" },
    { label: "Content Analysis", href: "/content/analyze", description: "Analyze your learning content" },
    { label: "Logout", href: "/logout", description: "Sign out of your account" }
  ]

  return (
    <nav className="w-full border-b bg-white/80 backdrop-blur-sm sticky top-0 z-[80]" role="navigation" aria-label="Main">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link 
            className="flex items-center text-lg font-bold text-gray-900 hover:text-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md px-2 py-1" 
            href="/"
          >
            AI Language Tutor
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {isAuthenticated ? (
              <>
                <Link 
                  className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500" 
                  href="/"
                >
                  Home
                </Link>
                
                <Dropdown
                  label="Lexical"
                  items={lexicalItems}
                  isOpen={activeDropdown === 'lexical'}
                  onToggle={() => handleDropdownToggle('lexical')}
                />
                
                <Dropdown
                  label="Grammar"
                  items={grammarItems}
                  isOpen={activeDropdown === 'grammar'}
                  onToggle={() => handleDropdownToggle('grammar')}
                />

                <Link
                  className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                  href="/cando"
                >
                  CanDo
                </Link>
                
                <Dropdown
                  label="Profile"
                  items={profileItems}
                  isOpen={activeDropdown === 'profile'}
                  onToggle={() => handleDropdownToggle('profile')}
                />

                <Link
                  className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                  href="/settings"
                >
                  Settings
                </Link>
              </>
            ) : (
              <>
                <Link 
                  className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500" 
                  href="/login"
                >
                  Login
                </Link>
                <Link 
                  className="px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500" 
                  href="/register"
                >
                  Sign Up
                </Link>
              </>
            )}

            <div className="ml-2 pl-2 border-l border-gray-200">
              <ThemeToggle />
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center space-x-2">
            <ThemeToggle />
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-expanded={isMobileMenuOpen}
              aria-label="Toggle mobile menu"
            >
              {isMobileMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 bg-white">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {isAuthenticated ? (
                <>
                  <Link
                    href="/"
                    className="block px-3 py-2 text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                    onClick={closeAllDropdowns}
                  >
                    Home
                  </Link>
                  
                  <div className="space-y-1">
                    <div className="px-3 py-2 text-sm font-semibold text-gray-500 uppercase tracking-wider">
                      Lexical
                    </div>
                    {lexicalItems.map((item, index) => (
                      <Link
                        key={index}
                        href={item.href}
                        className="block px-6 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                        onClick={closeAllDropdowns}
                      >
                        {item.label}
                      </Link>
                    ))}
                  </div>

                  <div className="space-y-1">
                    <div className="px-3 py-2 text-sm font-semibold text-gray-500 uppercase tracking-wider">
                      Grammar
                    </div>
                    {grammarItems.map((item, index) => (
                      <Link
                        key={index}
                        href={item.href}
                        className="block px-6 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                        onClick={closeAllDropdowns}
                      >
                        {item.label}
                      </Link>
                    ))}
                  </div>

                  <Link
                    href="/cando"
                    className="block px-3 py-2 text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                    onClick={closeAllDropdowns}
                  >
                    CanDo
                  </Link>

                  <div className="space-y-1">
                    <div className="px-3 py-2 text-sm font-semibold text-gray-500 uppercase tracking-wider">
                      Profile
                    </div>
                    {profileItems.map((item, index) => (
                      <Link
                        key={index}
                        href={item.href}
                        className="block px-6 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                        onClick={closeAllDropdowns}
                      >
                        {item.label}
                      </Link>
                    ))}
                  </div>

                  <Link
                    href="/settings"
                    className="block px-3 py-2 text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                    onClick={closeAllDropdowns}
                  >
                    Settings
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="block px-3 py-2 text-base font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                    onClick={closeAllDropdowns}
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    className="block px-3 py-2 text-base font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                    onClick={closeAllDropdowns}
                  >
                    Sign Up
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Overlay to close dropdowns when clicking outside */}
      {activeDropdown && (
        <div 
          className="fixed inset-0 z-[85]" 
          onClick={() => setActiveDropdown(null)}
        />
      )}
    </nav>
  )
}


