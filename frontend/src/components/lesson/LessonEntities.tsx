"use client";

import React from "react";

type WordRef = {
  text?: string;
  kanji?: string;
  hiragana?: string;
  wordId?: string | null;
  // From Neo4j Word nodes:
  orth?: string; // standard_orthography
  katakana?: string; // reading_katakana
  romaji?: string;
  pos?: string; // pos_primary
  translation?: string;
  source_text?: string;
  elementId?: string;
};

type GrammarRef = {
  pattern?: string;
  patternId?: string | null;
  // From Neo4j GrammarPattern nodes:
  id?: string;
  classification?: string;
};

function WordCard({ word }: { word: WordRef }) {
  const kanji = word.orth || word.kanji || word.text || word.source_text;
  const reading = word.katakana || word.hiragana;
  const romaji = word.romaji;
  const translation = word.translation;
  const pos = word.pos;
  const href = kanji
    ? `/lexical/graph?center=${encodeURIComponent(kanji)}`
    : undefined;

  return (
    <a
      href={href || "#"}
      className={`group block p-2.5 md:p-3 rounded-lg border transition-all ${
        href
          ? "bg-emerald-50 border-emerald-200 hover:bg-emerald-100 active:bg-emerald-200 hover:shadow-md cursor-pointer"
          : "bg-muted border-border"
      }`}
      title={href ? "Open in Lexical Graph" : undefined}
    >
      <div className="flex items-baseline gap-2 mb-1 flex-wrap">
        <div className="text-base md:text-lg font-medium text-foreground break-words">
          {kanji}
        </div>
        {pos && (
          <span className="text-xs text-emerald-600 font-mono uppercase shrink-0">
            {pos}
          </span>
        )}
      </div>

      {reading && (
        <div className="text-xs md:text-sm text-muted-foreground mb-1 break-words">
          {reading}
        </div>
      )}

      {romaji && (
        <div className="text-xs text-muted-foreground italic mb-1 break-words">
          {romaji}
        </div>
      )}

      {translation && (
        <div className="text-xs md:text-sm text-foreground font-medium break-words">
          {translation}
        </div>
      )}
    </a>
  );
}

function GrammarCard({ grammar }: { grammar: GrammarRef }) {
  const pattern = grammar.pattern;
  const classification = grammar.classification;
  const patternId = grammar.id || grammar.patternId;
  const href = patternId
    ? `/grammar/study/${encodeURIComponent(patternId)}`
    : undefined;

  return (
    <a
      href={href || "#"}
      className={`group block p-2.5 md:p-3 rounded-lg border transition-all ${
        href
          ? "bg-indigo-50 border-indigo-200 hover:bg-indigo-100 active:bg-indigo-200 hover:shadow-md cursor-pointer"
          : "bg-muted border-border"
      }`}
      title={href ? "Open Grammar Study" : undefined}
    >
      <div className="flex items-baseline justify-between gap-2 mb-1 flex-wrap">
        <div className="text-sm md:text-base font-medium text-foreground break-words flex-1">
          {pattern}
        </div>
        {classification && (
          <span className="text-xs text-indigo-600 font-mono uppercase shrink-0">
            {classification}
          </span>
        )}
      </div>

      {!href && (
        <div className="text-xs text-muted-foreground italic">
          Pattern not mapped
        </div>
      )}
    </a>
  );
}

export default function LessonEntities({
  words,
  grammar,
}: {
  words?: WordRef[];
  grammar?: GrammarRef[];
}) {
  const hasWords = words && words.length > 0;
  const hasGrammar = grammar && grammar.length > 0;

  if (!hasWords && !hasGrammar) {
    return null;
  }

  return (
    <div className="rounded-xl border border-border bg-card/70 backdrop-blur p-5 shadow-sm">
      {/* Words Section */}
      {hasWords && (
        <div className="mb-6 last:mb-0">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">📝</span>
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Vocabulary ({words.length})
            </h3>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {words.slice(0, 20).map((w, i) => (
              <WordCard key={`word-${i}-${w.elementId || w.text}`} word={w} />
            ))}
          </div>
          {words.length > 20 && (
            <div className="mt-2 text-xs text-muted-foreground text-center">
              + {words.length - 20} more words
            </div>
          )}
        </div>
      )}

      {/* Grammar Section */}
      {hasGrammar && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">📐</span>
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Grammar Patterns ({grammar.length})
            </h3>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {grammar.slice(0, 15).map((g, i) => (
              <GrammarCard
                key={`grammar-${i}-${g.id || g.pattern}`}
                grammar={g}
              />
            ))}
          </div>
          {grammar.length > 15 && (
            <div className="mt-2 text-xs text-muted-foreground text-center">
              + {grammar.length - 15} more patterns
            </div>
          )}
        </div>
      )}
    </div>
  );
}
