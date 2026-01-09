"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JapaneseText } from "@/components/text/JapaneseText";
import { Badge } from "@/components/ui/badge";
import type { GrammarPatternsCard as GrammarPatternsCardType } from "@/types/lesson-root";

interface GrammarPatternsCardProps {
  data: GrammarPatternsCardType;
}

export function GrammarPatternsCard({ data }: GrammarPatternsCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">Grammar Patterns</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.patterns.map((pattern, idx) => (
          <Card key={pattern.id} className="border-l-4 border-l-blue-500">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">
                Grammar Pattern {idx + 1}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 p-4 space-y-4">
              {/* Pattern form */}
              <div className="bg-blue-500/10 p-4 rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">
                  Pattern
                </div>
                <div className="text-lg font-semibold">
                  <JapaneseText data={pattern.form.ja} />
                </div>
              </div>

              {/* Explanation */}
              <div>
                <div className="text-sm text-muted-foreground mb-1">
                  Explanation
                </div>
                <JapaneseText data={pattern.explanation} />
              </div>

              {/* Slots */}
              {pattern.slots && pattern.slots.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-1">
                    Slots
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {pattern.slots.map((slot, slotIdx) => (
                      <Badge key={slotIdx} variant="secondary">
                        [{slot}]
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Examples */}
              {pattern.examples && pattern.examples.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-2">
                    Examples
                  </div>
                  <div className="space-y-2">
                    {pattern.examples.map((example, exIdx) => (
                      <div key={exIdx} className="pl-4 border-l-2 border-border">
                        <JapaneseText data={example.ja} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Classification badge */}
              {pattern.classification && (
                <div>
                  <Badge variant="outline">{pattern.classification}</Badge>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  );
}
