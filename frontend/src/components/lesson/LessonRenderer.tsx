"use client";

import React, { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { DialogueCard } from "./DialogueCard";
import { ReadingCard } from "./ReadingCard";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { JapaneseTextData } from "@/components/text/JapaneseText";

type MediaItem = { path: string; alt?: string };

type UICard = {
  id: string;
  kind: "text" | "dialogue" | "tips" | "list" | "image" | "reading";
  title?: any;
  subtitle?: string;
  body?: { jp?: string | JapaneseTextData; meta?: string | JapaneseTextData };
  bullets?: Array<string | JapaneseTextData>;
  badges?: string[];
  media?: MediaItem[];
  dialogue_turns?: Array<{ speaker: string; japanese: any; notes?: string }>;
  reading?: { title?: any; content: any; comprehension_questions?: string[] };
};

type UISection = {
  id: string;
  type: string;
  title?: string;
  cards?: UICard[];
};

type Variant = {
  lessonId: string;
  level: number;
  ui?: {
    header?: { title?: string; subtitle?: string; chips?: string[] };
    sections?: UISection[];
    gallery?: MediaItem[];
  };
};

// Helper to check if something is a JapaneseText object
function isJapaneseTextObject(item: unknown): item is JapaneseTextData {
  if (typeof item !== "object" || item === null) return false;
  const obj = item as Record<string, unknown>;
  return (
    typeof obj.kanji === "string" ||
    typeof obj.std === "string" ||
    typeof obj.romaji === "string" ||
    typeof obj.furigana === "string" ||
    Array.isArray(obj.furigana) ||
    typeof obj.translation === "string" ||
    (typeof obj.translation === "object" && obj.translation !== null)
  );
}

function MetaMarkdown({
  text,
  showTranslation = true,
}: {
  text?: any;
  showTranslation?: boolean;
}) {
  if (!text || !showTranslation) return null;

  // Handle JapaneseText objects
  if (isJapaneseTextObject(text)) {
    return (
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <JapaneseText data={text} />
      </div>
    );
  }

  // Handle regular strings
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

function DialogueBody({ body }: { body?: { jp?: any; meta?: any } }) {
  if (!body) return null;

  return (
    <div className="space-y-1">
      {body.jp &&
        (isJapaneseTextObject(body.jp) ? (
          <JapaneseText data={body.jp} />
        ) : (
          (body.jp || "")
            .split(/\n+/)
            .filter(Boolean)
            .map((ln: string, i: number) => (
              <div key={i} className="text-sm">
                {ln}
              </div>
            ))
        ))}
      {body.meta ? (
        isJapaneseTextObject(body.meta) ? (
          <JapaneseText data={body.meta} />
        ) : (
          <MetaMarkdown text={body.meta} />
        )
      ) : null}
    </div>
  );
}

function UICardView({
  card,
  showTranslations = true,
}: {
  card: UICard;
  showTranslations?: boolean;
}) {
  return (
    <Card className="border-0 shadow-sm bg-card/70 backdrop-blur">
      <CardHeader>
        {card.title ? (
          <CardTitle className="text-base">
            {isJapaneseTextObject(card.title) ? (
              <JapaneseText data={card.title} inline />
            ) : (
              card.title
            )}
          </CardTitle>
        ) : null}
        {card.subtitle ? (
          <CardDescription>{card.subtitle}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3">
        {card.kind === "dialogue" ? (
          <DialogueBody body={card.body} />
        ) : (
          <>
            {card.body?.jp ? (
              isJapaneseTextObject(card.body.jp) ? (
                <JapaneseText data={card.body.jp} />
              ) : (
                <div className="whitespace-pre-wrap text-sm">{card.body.jp}</div>
              )
            ) : null}
            {card.body?.meta ? (
              isJapaneseTextObject(card.body.meta) ? (
                <JapaneseText data={card.body.meta} />
              ) : (
                <MetaMarkdown
                  text={card.body.meta}
                  showTranslation={showTranslations}
                />
              )
            ) : null}
          </>
        )}
        {Array.isArray(card.bullets) && card.bullets.length > 0 ? (
          <ul className="list-disc ml-5 text-sm space-y-2">
            {card.bullets.slice(0, 8).map((b, i) => (
              <li key={i}>
                {isJapaneseTextObject(b) ? (
                  <JapaneseText data={b} inline />
                ) : (
                  <MetaMarkdown text={b} showTranslation={showTranslations} />
                )}
              </li>
            ))}
          </ul>
        ) : null}
        {Array.isArray(card.media) && card.media.length > 0 ? (
          <div className="grid grid-cols-2 gap-3">
            {card.media.map((m, i) => (
              <img
                key={i}
                src={m.path}
                alt={m.alt || "image"}
                className="w-full h-auto rounded"
              />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function LessonRenderer({
  variant,
  level = 3,
}: {
  variant: Variant | null;
  level?: number;
}) {
  const { applyLevelPreset } = useDisplaySettings();

  // Apply level preset when level changes
  useEffect(() => {
    if (level) {
      applyLevelPreset(level);
    }
  }, [level, applyLevelPreset]);

  if (!variant || !variant.ui) return null;

  // Legacy level-based display settings (for backward compatibility)
  const showTranslations = level <= 3;

  const header = variant.ui.header || {};
  const sections = variant.ui.sections || [];
  const enhancedMap: Record<string, boolean> =
    (variant as any)?.metadata?.stage2EnhancedMap || {};

  // Render card based on kind
  const renderCard = (card: UICard) => {
    switch (card.kind) {
      case "dialogue":
        // Use new multilingual DialogueCard if dialogue_turns exist
        if (card.dialogue_turns && card.dialogue_turns.length > 0) {
          return <DialogueCard {...card} />;
        }
        // Fallback to old format
        return <UICardView card={card} showTranslations={showTranslations} />;
      case "reading":
        // Use new multilingual ReadingCard
        if (card.reading) {
          return <ReadingCard {...card} />;
        }
        return <UICardView card={card} showTranslations={showTranslations} />;
      default:
        // Use default card view for other types
        return <UICardView card={card} showTranslations={showTranslations} />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Add level indicator badge */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
        <span>Display Level: {level}</span>
        {level <= 2 && (
          <span className="px-2 py-0.5 bg-blue-100 text-blue-600 rounded text-xs">
            Beginner (with romaji)
          </span>
        )}
        {level >= 3 && level <= 4 && (
          <span className="px-2 py-0.5 bg-green-100 text-green-600 rounded text-xs">
            Intermediate
          </span>
        )}
        {level >= 5 && (
          <span className="px-2 py-0.5 bg-purple-100 text-purple-600 rounded text-xs">
            Advanced (no aids)
          </span>
        )}
      </div>

      {(header.title || header.subtitle) && (
        <div className="rounded-xl border bg-gradient-to-br from-background to-muted p-5 shadow-sm">
          {header.title ? (
            <div className="text-xl font-semibold">{header.title}</div>
          ) : null}
          {header.subtitle ? (
            <div className="mt-1 text-sm text-muted-foreground">
              {isJapaneseTextObject(header.subtitle) ? (
                <JapaneseText data={header.subtitle} inline />
              ) : (
                <MetaMarkdown text={header.subtitle} />
              )}
            </div>
          ) : null}
          {Array.isArray(header.chips) && header.chips.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {header.chips.map((c, i) => (
                <span
                  key={i}
                  className="text-xs rounded-full bg-muted px-2 py-1 text-muted-foreground"
                >
                  {c}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}

      {sections
        .filter((sec) => (sec.cards || []).length > 0)
        .map((sec) => (
          <div key={sec.id} className="space-y-3">
            {sec.title ? (
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <span>{sec.title}</span>
                {enhancedMap[sec.id] || enhancedMap[sec.type] ? (
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-[10px] uppercase tracking-wide">
                    Enhanced
                  </span>
                ) : null}
              </div>
            ) : null}
            <div className="grid grid-cols-1 gap-3">
              {(sec.cards || []).map((card) => (
                <div key={card.id}>{renderCard(card)}</div>
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}
