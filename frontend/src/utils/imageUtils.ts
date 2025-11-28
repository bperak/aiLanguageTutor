/**
 * Utility for resolving image paths in frontend.
 */

/**
 * Resolves a relative image path to an absolute URL for Next.js.
 * Handles both local dev and production paths.
 * 
 * @param path - Relative path from repo root (e.g., "images/lessons/cando/JF_106/image-1.png")
 * @returns Absolute URL path (e.g., "/images/lessons/cando/JF_106/image-1.png")
 */
export function resolveImagePath(path: string | null | undefined): string | null {
  if (!path) return null
  
  // Already absolute?
  if (path.startsWith('/') || path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  
  // Ensure it starts with /
  return path.startsWith('/') ? path : `/${path}`
}

/**
 * Gets the full image URL for display.
 * Images are generated directly to frontend/public/images/ so Next.js serves them.
 * 
 * @param path - Relative path from repo root (e.g., "images/lessons/cando/JF_105/image.png")
 * @returns Full URL for image display (e.g., "/images/lessons/cando/JF_105/image.png") or null if invalid
 */
export function getImageUrl(path: string | null | undefined): string | null {
  if (!path) {
    if (process.env.NODE_ENV === 'development') {
      console.debug('[getImageUrl] No path provided')
    }
    return null
  }
  
  const resolved = resolveImagePath(path)
  if (!resolved) {
    if (process.env.NODE_ENV === 'development') {
      console.debug('[getImageUrl] Failed to resolve path:', path)
    }
    return null
  }
  
  // Filter out placeholder/invalid URLs (like example.com) that LLM might generate
  // These should be treated as no image rather than trying to load from external hosts
  if (resolved.startsWith('http://') || resolved.startsWith('https://')) {
    try {
      // Check for placeholder domains
      const placeholderDomains = ['example.com', 'example.org', 'placeholder.com', 'placehold.it']
      const url = new URL(resolved)
      if (placeholderDomains.some(domain => url.hostname.includes(domain))) {
        if (process.env.NODE_ENV === 'development') {
          console.debug('[getImageUrl] Placeholder URL detected:', resolved)
        }
        return null // Invalid placeholder URL
      }
      // For real external URLs, we'd need to configure them in next.config.js
      // For now, only allow local paths
      return null
    } catch (e) {
      // Invalid URL format, treat as no image
      return null
    }
  }
  
  // Next.js serves static files from public/ directory at the root URL
  // Images are generated directly to frontend/public/images/ so they're accessible at /images/...
  // Ensure path starts with / and doesn't have double slashes
  let cleanPath = resolved.startsWith('/') ? resolved : `/${resolved}`
  
  // Remove any double slashes (except at the start)
  cleanPath = cleanPath.replace(/([^:]\/)\/+/g, '$1')
  
  // Ensure it doesn't start with double slash
  if (cleanPath.startsWith('//')) {
    cleanPath = cleanPath.substring(1)
  }
  
  if (process.env.NODE_ENV === 'development') {
    console.debug('[getImageUrl] Resolved image path:', {
      original: path,
      resolved: resolved,
      clean: cleanPath,
      fullUrl: typeof window !== 'undefined' ? `${window.location.origin}${cleanPath}` : null
    })
  }
  
  return cleanPath
}

