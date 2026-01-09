"use client";

import React, { useState } from "react";
import Image from "next/image";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JapaneseText } from "@/components/text/JapaneseText";
import { Badge } from "@/components/ui/badge";
import { getImageUrl } from "@/utils/imageUtils";
import type { WordsCard as WordsCardType } from "@/types/lesson-root";

// Component with fallback for missing images
function ImageWithFallback({
  src,
  alt,
  prompt,
  originalPath,
}: {
  src: string;
  alt: string;
  prompt?: string;
  originalPath?: string;
}) {
  const [hasError, setHasError] = useState(false);

  if (hasError || !src) {
    return (
      <div className="h-full flex items-center justify-center bg-muted">
        <span className="text-xs text-muted-foreground text-center px-2">
          {prompt?.substring(0, 50) || "Image not available"}...
        </span>
      </div>
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      fill
      className="object-cover"
      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      unoptimized={true}
      onError={() => {
        // Missing images are expected when image generation is disabled or deferred
        if (process.env.NODE_ENV === "development") {
          console.warn("[WordsCard] Image load failed (showing fallback):", {
            src,
            originalPath,
            prompt: prompt?.substring(0, 50),
          });
        }
        setHasError(true);
      }}
      onLoad={() => {
        if (process.env.NODE_ENV === "development") {
          console.debug("[WordsCard] Image loaded successfully:", src);
        }
      }}
    />
  );
}

interface WordsCardProps {
  data: WordsCardType;
}

export function WordsCard({ data }: WordsCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">Vocabulary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((item) => {
            const imageUrl = item.image ? getImageUrl(item.image.path) : null;
            const hasImagePath = imageUrl !== null;

            return (
              <Card key={item.id} className="hover:shadow-lg transition-shadow">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    <JapaneseText data={item.jp} />
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 p-4">
                  {/* Image display */}
                  {item.image && (
                    <div className="mb-3 relative w-full h-32 rounded-lg overflow-hidden bg-muted">
                      {hasImagePath ? (
                        <ImageWithFallback
                          src={imageUrl}
                          alt={item.image.prompt?.substring(0, 50) || "Image"}
                          prompt={item.image.prompt}
                          originalPath={item.image.path ?? undefined}
                        />
                      ) : (
                        <div className="h-full flex items-center justify-center">
                          <span className="text-sm text-muted-foreground text-center px-2">
                            {item.image.prompt?.substring(0, 50) ||
                              "No image prompt"}
                            ...
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Tags */}
                  {item.tags && item.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {item.tags.map((tag, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
