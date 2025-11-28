"use client"

import React, { useMemo, useState } from "react"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { JapaneseText } from "@/components/text/JapaneseText"
import { getImageUrl } from "@/utils/imageUtils"
import type { DialogueCard as DialogueCardType } from "@/types/lesson-root"
import { Button } from "@/components/ui/button"
import { extendDialogue, newDialogue as apiNewDialogue, storeDialogue } from "@/lib/api/dialogue"

interface LessonDialogueCardProps {
  data: DialogueCardType
  canDoId?: string
}

export function LessonDialogueCard({ data, canDoId }: LessonDialogueCardProps) {
  const imageUrl = data.image ? getImageUrl(data.image.path) : null
  const hasImagePath = imageUrl !== null
  const [setting, setSetting] = useState<string | undefined>(data.setting || undefined)
  const [turns, setTurns] = useState(data.turns)
  const [loading, setLoading] = useState<"more" | "new" | "store" | null>(null)
  const canGenerate = Boolean(canDoId)

  // Convert current JPText turns to DialogueTurnPayload expected by backend
  const payloadTurns = useMemo(() => turns.map(t => ({
    speaker: t.speaker,
    japanese: {
      kanji: t.ja.std || t.ja.kanji || "",
      romaji: t.ja.romaji || "",
      furigana: Array.isArray(t.ja.furigana) ? t.ja.furigana : (t.ja.std ? [{ text: t.ja.std }] : []),
      translation: typeof t.ja.translation === 'string' ? t.ja.translation : (t.ja.translation?.en || ""),
    },
  })), [turns])

  const onMore = async () => {
    if (!canDoId) return
    setLoading("more")
    try {
      const card = await extendDialogue({
        can_do_id: canDoId,
        setting: setting || "",
        // Send no context turns to avoid schema 422 when fields are missing
        num_turns: 3,
      })
      // Convert returned ML dialogue_turns to our JPText structure
      const newTurns = (card.dialogue_turns || []).map((t: any) => ({
        speaker: t.speaker,
        ja: {
          kanji: t.japanese?.kanji,
          std: t.japanese?.kanji,
          romaji: t.japanese?.romaji,
          furigana: t.japanese?.furigana,
          translation: t.japanese?.translation,
        },
      }))
      setTurns(newTurns)
      setSetting(card.setting)
    } finally {
      setLoading(null)
    }
  }

  const onNew = async () => {
    if (!canDoId) return
    setLoading("new")
    try {
      const card = await apiNewDialogue({
        can_do_id: canDoId,
        seed_setting: setting,
        num_turns: 6,
      })
      const newTurns = (card.dialogue_turns || []).map((t: any) => ({
        speaker: t.speaker,
        ja: {
          kanji: t.japanese?.kanji,
          std: t.japanese?.kanji,
          romaji: t.japanese?.romaji,
          furigana: t.japanese?.furigana,
          translation: t.japanese?.translation,
        },
      }))
      setTurns(newTurns)
      setSetting(card.setting)
    } finally {
      setLoading(null)
    }
  }

  const onStore = async () => {
    if (!canDoId) return
    setLoading("store")
    try {
      await storeDialogue({
        can_do_id: canDoId,
        dialogue_card: { setting, dialogue_turns: payloadTurns },
      })
    } finally {
      setLoading(null)
    }
  }

  // Debug logging (only in dev)
  if (process.env.NODE_ENV === 'development' && data.image) {
    console.log('[LessonDialogueCard] Image data:', {
      path: data.image.path,
      resolvedUrl: imageUrl,
      hasImagePath,
      prompt: data.image.prompt
    })
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">
          <JapaneseText data={data.title} />
        </CardTitle>
        {data.notes_en && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{data.notes_en}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {setting && (
          <div className="text-sm text-gray-700 whitespace-pre-wrap">{setting}</div>
        )}
        {/* Image display */}
        {data.image && (
          <div className="mb-4 relative w-full h-48 rounded-lg overflow-hidden bg-gradient-to-r from-blue-100 to-green-100 dark:from-blue-900 dark:to-green-900">
            {hasImagePath ? (
              <Image
                src={imageUrl!}
                alt={data.image.prompt}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 768px"
                unoptimized={true}
                onError={(e) => {
                  if (process.env.NODE_ENV === 'development') {
                    console.error('[LessonDialogueCard] Image load error:', imageUrl, e)
                  }
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center">
                <span className="text-sm text-gray-600 dark:text-gray-400 text-center px-4">
                  {data.image.prompt}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Dialogue turns */}
        <div className="space-y-3">
          {turns.map((turn, idx) => (
            <div
              key={idx}
              className={`flex ${idx % 2 === 0 ? "justify-start" : "justify-end"}`}
            >
              <div className={`max-w-[80%] ${idx % 2 === 0 ? "" : "text-right"}`}>
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  {turn.speaker}
                </div>
                <div
                  className={`rounded-lg p-3 ${
                    idx % 2 === 0
                      ? "bg-gray-100 dark:bg-gray-800"
                      : "bg-blue-100 dark:bg-blue-900"
                  }`}
                >
                  <JapaneseText data={turn.ja as any} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="pt-2 flex gap-2">
          <Button size="sm" variant="secondary" onClick={onMore} disabled={!canGenerate || loading !== null}>
            {loading === "more" ? "Generating…" : "More dialogue"}
          </Button>
          <Button size="sm" variant="secondary" onClick={onNew} disabled={!canGenerate || loading !== null}>
            {loading === "new" ? "Generating…" : "New dialogue"}
          </Button>
          <Button size="sm" variant="outline" onClick={onStore} disabled={!canGenerate || loading !== null}>
            {loading === "store" ? "Saving…" : "Store"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

