"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { JapaneseText } from "@/components/text/JapaneseText";
import type { FormulaicExpressionsCard as FormulaicExpressionsCardType } from "@/types/lesson-root";

interface FormulaicExpressionsCardProps {
  data: FormulaicExpressionsCardType;
}

export function FormulaicExpressionsCard({
  data,
}: FormulaicExpressionsCardProps) {
  const title = data.title?.en || data.title?.ja || "Formulaic Expressions";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.items && data.items.length > 0 ? (
          data.items.map((item, idx) => (
            <div key={item.id || idx} className="border-b pb-4 last:border-b-0">
              <div className="mb-2">
                <JapaneseText data={item.expression} />
              </div>
              {item.context && (
                <div className="text-sm text-muted-foreground mb-2">
                  <strong>Context:</strong>{" "}
                  {item.context.en ||
                    item.context.ja ||
                    Object.values(item.context)[0]}
                </div>
              )}
              {item.examples && item.examples.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="text-sm font-semibold text-muted-foreground">
                    Examples:
                  </div>
                  {item.examples.map((example, exIdx) => (
                    <div key={exIdx} className="text-sm">
                      <JapaneseText data={example} />
                    </div>
                  ))}
                </div>
              )}
              {item.tags && item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {item.tags.map((tag, tagIdx) => (
                    <Badge key={tagIdx} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <p className="text-muted-foreground italic">
            No formulaic expressions available
          </p>
        )}
      </CardContent>
    </Card>
  );
}
