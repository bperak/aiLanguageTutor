/**
 * Utilities for converting legacy text formats to new multilingual structures.
 */

export interface FuriganaSegment {
  text: string;
  ruby?: string;
}

/**
 * Parse markdown-style furigana annotations
 * 
 * Format: [漢字](#furi "ふりがな")
 * 
 * Example:
 *   Input:  "今日は[日曜日](#furi \"にちようび\")です。"
 *   Output: [
 *     { text: "今日" },
 *     { text: "は" },
 *     { text: "日曜日", ruby: "にちようび" },
 *     { text: "です。" }
 *   ]
 */
export function parseLegacyFurigana(text: string): FuriganaSegment[] {
  const segments: FuriganaSegment[] = [];

  // Regex to match: [kanji](#furi "reading") or plain text
  const regex = /\[([^\]]+)\]\(#furi\s+"([^"]+)"\)|([^\[]+)/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match[1] && match[2]) {
      // Found furigana annotation: [kanji](#furi "reading")
      segments.push({ text: match[1], ruby: match[2] });
    } else if (match[3]) {
      // Found plain text without furigana
      segments.push({ text: match[3] });
    }
  }
  return segments;
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
  const kanji = legacyText.replace(/\[([^\]]+)\]\(#furi\s+"[^"]+"\)/g, "$1");
  return {
    kanji,
    romaji,
    furigana: parseLegacyFurigana(legacyText),
    translation,
  };
}
