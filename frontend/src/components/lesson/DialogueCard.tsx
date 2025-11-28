"use client"

import React, { useMemo, useState } from "react"
import { JapaneseText } from "@/components/text/JapaneseText"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { extendDialogue, newDialogue as apiNewDialogue, storeDialogue } from "@/lib/api/dialogue"

type DialogueTurn = {
  speaker: string
  japanese: {
    kanji: string
    romaji?: string
    furigana?: Array<{ text: string; ruby?: string }>
    translation?: string
  }
  notes?: string
}

type DialogueCardProps = {
  title?: any
  setting?: string
  characters?: string[]
  dialogue_turns?: DialogueTurn[]
  canDoId?: string
}

export function DialogueCard({ title, setting, characters, dialogue_turns, canDoId }: DialogueCardProps) {
  const [turns, setTurns] = useState<DialogueTurn[]>(dialogue_turns || [])
  const [opening, setOpening] = useState<string | undefined>(setting)
  const [loading, setLoading] = useState<"more" | "new" | "store" | null>(null)
  const canGenerate = Boolean(canDoId)

  const payloadTurns = useMemo(() =>
    turns.map(t => ({ speaker: t.speaker, japanese: t.japanese, notes: t.notes })),
  [turns])

  const onMore = async () => {
    if (!canDoId) return
    setLoading("more")
    try {
      const card = await extendDialogue({
        can_do_id: canDoId,
        setting: opening || "",
        characters: characters,
        dialogue_turns: payloadTurns,
        num_turns: 3,
      })
      setTurns(card.dialogue_turns || [])
      setOpening(card.setting)
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
        seed_setting: opening,
        characters: characters,
        num_turns: 6,
      })
      setTurns(card.dialogue_turns || [])
      setOpening(card.setting)
    } finally {
      setLoading(null)
    }
  }

  const onStore = async () => {
    if (!canDoId) return
    setLoading("store")
    try {
      await storeDialogue({ can_do_id: canDoId, dialogue_card: { setting: opening, characters, dialogue_turns: payloadTurns } })
    } finally {
      setLoading(null)
    }
  }
  return (
    <Card className="border-0 shadow-sm bg-white/70 backdrop-blur">
      <CardHeader>
        {title && <CardTitle className="text-base">
          {typeof title === 'string' ? title : <JapaneseText data={title} inline />}
        </CardTitle>}
      </CardHeader>
      <CardContent className="space-y-4">
        {opening && (
          <div className="text-sm text-gray-700 whitespace-pre-wrap">{opening}</div>
        )}
        {turns?.map((turn, i) => (
          <div key={i} className="space-y-1">
            <div className="font-semibold text-sm text-gray-700">
              {turn.speaker}:
            </div>
            <div className="pl-4 border-l-2 border-gray-200">
              <JapaneseText data={turn.japanese} />
              {turn.notes && (
                <div className="text-xs text-gray-500 italic mt-1">
                  💡 {turn.notes}
                </div>
              )}
            </div>
          </div>
        ))}
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

