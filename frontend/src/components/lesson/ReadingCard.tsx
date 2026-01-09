"use client";

import React from "react";
import { JapaneseText } from "@/components/text/JapaneseText";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { JPText } from "@/types/lesson-root";

type ReadingCardProps = {
  title?: any;
  reading?: {
    title?: any;
    content: any;
    comprehension_questions?: string[];
    comprehension?: Array<{
      q: string | JPText;
      a: string | JPText;
      evidenceSpan?: string | null;
    }>;
  };
};

export function ReadingCard({ title, reading }: ReadingCardProps) {
  if (!reading) return null;

  return (
    <Card className="border-0 shadow-sm bg-card/70 backdrop-blur">
      <CardHeader>
        {title && (
          <CardTitle className="text-base">
            {typeof title === "string" ? (
              title
            ) : (
              <JapaneseText data={title} inline />
            )}
          </CardTitle>
        )}
        {reading.title && (
          <div className="text-lg font-medium mt-2">
            <JapaneseText data={reading.title} inline />
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="prose prose-sm max-w-none">
          <JapaneseText data={reading.content} />
        </div>

        {reading.comprehension && reading.comprehension.length > 0 ? (
          <div className="mt-4 pt-4 border-t">
            <div className="text-sm font-medium mb-2">
              Comprehension Questions:
            </div>
            <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
              {reading.comprehension.map((qa, i) => (
                <li key={i} className="mb-4">
                  <div className="mb-1">
                    {typeof qa.q === "string" ? (
                      qa.evidenceSpan ? (
                        (() => {
                          const ev = qa.evidenceSpan;
                          const idx = qa.q.indexOf(ev);
                          if (idx >= 0) {
                            const before = qa.q.slice(0, idx);
                            const match = qa.q.slice(idx, idx + ev.length);
                            const after = qa.q.slice(idx + ev.length);
                            return (
                              <span>
                                {before}
                                <mark className="bg-yellow-200 px-0.5 rounded">
                                  {match}
                                </mark>
                                {after}
                              </span>
                            );
                          }
                          return <span>{qa.q}</span>;
                        })()
                      ) : (
                        <span>{qa.q}</span>
                      )
                    ) : (
                      <JapaneseText data={qa.q} inline />
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 ml-6">
                    <span className="font-medium">Answer: </span>
                    {typeof qa.a === "string" ? (
                      <span>{qa.a}</span>
                    ) : (
                      <JapaneseText data={qa.a} inline />
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          reading.comprehension_questions &&
          reading.comprehension_questions.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <div className="text-sm font-medium mb-2">
                Comprehension Questions:
              </div>
              <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
                {reading.comprehension_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ol>
            </div>
          )
        )}
      </CardContent>
    </Card>
  );
}
