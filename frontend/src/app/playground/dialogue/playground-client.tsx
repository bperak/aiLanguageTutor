"use client";

import { useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { DialogueCard } from "@/components/lesson/DialogueCard";

export function DialoguePlaygroundClient() {
  const sp = useSearchParams();
  const canDoId = sp.get("canDoId") || "JF_105";
  const title = sp.get("title") || "Dialogue Playground";
  const setting =
    sp.get("setting") || "A simple setting for testing the dialogue actions.";
  const initial = useMemo(
    () => [
      {
        speaker: "A",
        japanese: {
          kanji: "こんにちは。",
          romaji: "konnichiwa",
          furigana: [{ text: "こんにちは" }],
          translation: "Hello.",
        },
      },
      {
        speaker: "B",
        japanese: {
          kanji: "元気ですか。",
          romaji: "genki desu ka",
          furigana: [{ text: "元気" }, { text: "ですか" }],
          translation: "How are you?",
        },
      },
    ],
    []
  );

  return (
    <div className="max-w-3xl mx-auto p-6">
      <Card className="mb-4">
        <CardContent className="pt-6">
          Use the buttons below to exercise the dialogue generation endpoints.
        </CardContent>
      </Card>
      <DialogueCard
        title={title}
        setting={setting}
        characters={["A", "B"]}
        dialogue_turns={initial as any}
        canDoId={canDoId}
      />
    </div>
  );
}
