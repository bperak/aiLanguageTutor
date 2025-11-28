"use client"

import React from "react"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { JapaneseText } from "@/components/text/JapaneseText"
import { getImageUrl } from "@/utils/imageUtils"
import type { CultureCard as CultureCardType } from "@/types/lesson-root"

// Helper to extract text from bilingual or JapaneseText format (for fallback)
function extractBilingualText(data: any, preferLanguage: 'en' | 'ja' = 'en'): string {
  if (!data) return ''
  
  // If it's a bilingual object {en: "...", ja: "..."}
  if (typeof data === 'object' && (data.en || data.ja)) {
    return data[preferLanguage] || data.en || data.ja || ''
  }
  
  // If it's a string
  if (typeof data === 'string') {
    return data
  }
  
  // If it's JapaneseText format
  if (data.std || data.kanji) {
    return data.std || data.kanji || ''
  }
  
  return ''
}

// Check if data is in JapaneseText format
function isJapaneseTextFormat(data: any): boolean {
  if (!data || typeof data !== 'object') return false
  // Must have at least std/kanji or furigana or romaji
  return !!(data.std || data.kanji || data.furigana || data.romaji)
}

interface CultureCardProps {
  data: CultureCardType
}

export function CultureCard({ data }: CultureCardProps) {
  if (!data) return null
  
  // Defensive check for title
  const hasJapaneseTitle = isJapaneseTextFormat(data.title)
  const titleEn = extractBilingualText(data.title, 'en')
  const titleJa = extractBilingualText(data.title, 'ja')
  
  // Defensive check for body
  const hasJapaneseBody = isJapaneseTextFormat(data.body)
  const bodyEn = extractBilingualText(data.body, 'en')
  const bodyJa = extractBilingualText(data.body, 'ja')
  
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">
          {hasJapaneseTitle ? (
            <JapaneseText data={data.title} />
          ) : (
            <>
              {titleEn}
              {titleJa && <div className="text-lg font-normal text-gray-600 dark:text-gray-300 mt-1">{titleJa}</div>}
            </>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Image display */}
        {data.image && (() => {
          const imageUrl = getImageUrl(data.image.path)
          const hasImagePath = imageUrl !== null
          
          return (
            <div className="mb-4 relative w-full h-64 rounded-lg overflow-hidden bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900 dark:to-pink-900">
              {hasImagePath ? (
                <Image
                  src={imageUrl}
                  alt={data.image.prompt}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 768px"
                  unoptimized={true}
                />
              ) : (
                <div className="h-full flex items-center justify-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400 text-center px-4">
                    {data.image.prompt}
                  </span>
                </div>
              )}
            </div>
          )
        })()}

        {/* Body content */}
        <div className="prose dark:prose-invert max-w-none">
          {hasJapaneseBody ? (
            <JapaneseText data={data.body} />
          ) : (
            <div className="space-y-4">
              {bodyEn && <p className="text-base leading-relaxed">{bodyEn}</p>}
              {bodyJa && (
                <p className="text-base leading-relaxed text-gray-700 dark:text-gray-300 border-l-4 border-purple-300 pl-4">
                  {bodyJa}
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

