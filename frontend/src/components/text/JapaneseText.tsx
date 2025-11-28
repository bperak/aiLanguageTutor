"use client"

import React from "react"
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext"

type FuriganaSegment = {
  text: string
  ruby?: string
}

type JapaneseTextData = {
  kanji?: string  // Old format
  std?: string    // V2 format (standard Japanese text)
  romaji?: string
  furigana?: FuriganaSegment[] | string  // Can be array (old) or inline string (v2: "漢{かん}字{じ}")
  translation?: string | Record<string, string>  // Can be string or {en: "...", ja: "..."}
}

type JapaneseTextProps = {
  data: JapaneseTextData
  className?: string
  inline?: boolean
  forceSettings?: Partial<ReturnType<typeof useDisplaySettings>['settings']>
}

/**
 * Parse inline furigana format "漢{かん}字{じ}" into segment array
 * @param furiganaStr - Inline furigana string like "休{やす}む"
 * @returns Array of segments like [{text: "休", ruby: "やす"}, {text: "む"}]
 */
function parseInlineFurigana(furiganaStr: string): FuriganaSegment[] {
  const segments: FuriganaSegment[] = []
  const regex = /([^{]+)(?:\{([^}]+)\})?/g
  let match
  
  while ((match = regex.exec(furiganaStr)) !== null) {
    const text = match[1]
    const ruby = match[2]
    
    if (text) {
      segments.push({ text, ruby })
    }
  }
  
  return segments
}

export function JapaneseText({ 
  data, 
  className = '', 
  inline = false,
  forceSettings 
}: JapaneseTextProps) {
  const { settings: contextSettings } = useDisplaySettings()
  const settings = forceSettings ? { ...contextSettings, ...forceSettings } : contextSettings

  if (!data) return null

  // Get base text (v2 uses 'std', old uses 'kanji')
  const baseText = data.std || data.kanji || ''
  
  // Get translation text (v2 uses object like {en: "..."}, old uses string)
  const translationText = typeof data.translation === 'string' 
    ? data.translation 
    : (data.translation?.en || data.translation?.ja || '')
  
  // If no content at all, return null
  if (!baseText && !translationText) {
    return null
  }
  
  // Debug logging (only in dev)
  if (process.env.NODE_ENV === 'development' && baseText) {
    console.log('[JapaneseText]', {
      baseText,
      furigana: data.furigana || 'NO FURIGANA',
      furiganaType: typeof data.furigana,
      showFurigana: settings.showFurigana,
      showKanji: settings.showKanji,
      level: settings.level,
      fullData: data
    })
  }

  const renderFurigana = () => {
    // Handle both string and array formats
    let segments: FuriganaSegment[] = []
    
    if (!data.furigana) {
      return <span>{baseText}</span>
    }
    
    // Parse inline format if string, otherwise use array directly
    if (typeof data.furigana === 'string') {
      segments = parseInlineFurigana(data.furigana)
    } else if (Array.isArray(data.furigana)) {
      segments = data.furigana
    }
    
    // If no segments or segments don't cover the text, fall back to base text
    if (segments.length === 0) {
      return <span>{baseText}</span>
    }
    
    // Check if segments cover the base text (allow for small differences)
    const segmentText = segments.map(s => s.text || '').join('')
    const baseTextNormalized = baseText.replace(/\s+/g, '')
    const segmentTextNormalized = segmentText.replace(/\s+/g, '')
    
    // If segments don't match base text reasonably, use base text with furigana hints if available
    if (segmentTextNormalized && segmentTextNormalized.length > 0) {
      // Render segments with furigana
      return segments.map((segment, i) => {
        if (segment.ruby && settings.showFurigana) {
          return (
            <ruby key={i} className="ruby-text">
              {segment.text || ''}
              <rt className="text-[0.6em] leading-none opacity-70 select-none">
                {segment.ruby}
              </rt>
            </ruby>
          )
        }
        return <span key={i}>{segment.text || ''}</span>
      })
    }
    
    // Fallback: show base text
    return <span>{baseText}</span>
  }

  const Container = inline ? 'span' : 'div'
  const spacing = inline ? '' : 'space-y-1'

  return (
    <Container className={`${spacing} ${className}`}>
      {/* Kanji/Standard text with optional furigana */}
      {settings.showKanji && baseText && (
        <div className={inline ? 'inline' : 'text-base leading-relaxed'}>
          {settings.showFurigana ? renderFurigana() : baseText}
        </div>
      )}
      
      {/* Romaji */}
      {settings.showRomaji && data.romaji && (
        <div className={`text-sm text-gray-600 italic ${inline ? 'inline ml-2' : ''}`}>
          {data.romaji}
        </div>
      )}
      
      {/* Translation */}
      {settings.showTranslation && translationText && (
        <div className={`text-sm text-gray-700 border-l-2 border-blue-300 pl-3 ${inline ? 'inline ml-2' : ''}`}>
          {translationText}
        </div>
      )}
    </Container>
  )
}

// Convenience wrapper for inline usage
export function InlineJapanese({ data, className }: Omit<JapaneseTextProps, 'inline'>) {
  return <JapaneseText data={data} className={className} inline />
}

