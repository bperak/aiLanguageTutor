/**
 * Legacy Format Converter
 * 
 * Converts old markdown-style furigana format to new structured format.
 * Old format: [今日](#furi "きょう")は[日曜日](#furi "にちようび")です。
 * New format: Array of FuriganaSegment objects
 */

export type FuriganaSegment = {
  text: string
  ruby?: string
}

/**
 * Parse legacy markdown-style furigana into structured segments
 * 
 * @param text - Text with markdown furigana: [今日](#furi "きょう")
 * @returns Array of FuriganaSegment objects
 * 
 * @example
 * const segments = parseLegacyFurigana('[今日](#furi "きょう")は[日曜日](#furi "にちようび")です。')
 * // Returns:
 * // [
 * //   { text: "今日", ruby: "きょう" },
 * //   { text: "は" },
 * //   { text: "日曜日", ruby: "にちようび" },
 * //   { text: "です。" }
 * // ]
 */
export function parseLegacyFurigana(text: string): FuriganaSegment[] {
  const segments: FuriganaSegment[] = []
  
  // Regex to match: [kanji](#furi "reading") or plain text
  const regex = /\[([^\]]+)\]\(#furi\s+"([^"]+)"\)|([^\[]+)/g
  
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match[1] && match[2]) {
      // Found furigana annotation: [kanji](#furi "reading")
      segments.push({ text: match[1], ruby: match[2] })
    } else if (match[3]) {
      // Found plain text without furigana
      segments.push({ text: match[3] })
    }
  }
  
  return segments
}

/**
 * Convert a string with legacy furigana to new multilingual structure
 * 
 * @param legacyText - Text with markdown furigana
 * @param translation - Optional English translation
 * @param romaji - Optional romanization
 * @returns JapaneseText object
 */
export function convertLegacyToMultilingual(
  legacyText: string,
  translation?: string,
  romaji?: string
) {
  // Extract plain kanji (without furigana annotations)
  const kanji = legacyText.replace(/\[([^\]]+)\]\(#furi\s+"[^"]+"\)/g, '$1')
  
  return {
    kanji,
    romaji,
    furigana: parseLegacyFurigana(legacyText),
    translation
  }
}

