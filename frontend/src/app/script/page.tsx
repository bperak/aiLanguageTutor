"use client";
import React, { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen, Target, TrendingUp } from "lucide-react";
export default function ScriptPage() {
  const [selectedType, setSelectedType] = useState<
    "hiragana" | "katakana" | null
  >(null);
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground leading-tight">
          // Japanese Scripts
        </h1>
        <p className="text-muted-foreground mt-2">
          // Learn Hiragana and Katakana through interactive practice
        </p>
      </div>

      {/* Script Type Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Card
          className={`cursor-pointer transition-all hover:shadow-lg ${
            selectedType === "hiragana" ? "ring-2 ring-primary" : ""
          }`}
          onClick={() => setSelectedType("hiragana")}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              // Hiragana
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              // Learn the basic Japanese syllabary used for native words and
              // grammar.
            </p>
            <div className="text-4xl mb-4">あいうえお</div>
            {selectedType === "hiragana" && (
              <div className="flex gap-2 mt-4">
                <Link href="/script/practice?type=hiragana">
                  <Button>Start Practice</Button>
                </Link>
                <Link href="/script/progress?type=hiragana">
                  <Button variant="outline">View Progress</Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <Card
          className={`cursor-pointer transition-all hover:shadow-lg ${
            selectedType === "katakana" ? "ring-2 ring-primary" : ""
          }`}
          onClick={() => setSelectedType("katakana")}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              // Katakana
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              // Learn the script used for foreign words, loanwords, and emphasis.
            </p>
            <div className="text-4xl mb-4">アイウエオ</div>
            {selectedType === "katakana" && (
              <div className="flex gap-2 mt-4">
                <Link href="/script/practice?type=katakana">
                  <Button>Start Practice</Button>
                </Link>
                <Link href="/script/progress?type=katakana">
                  <Button variant="outline">View Progress</Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/script/practice">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Target className="w-4 h-4" />
                // Practice
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                // Practice kana recognition and typing
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/script/progress">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="w-4 h-4" />
                // Progress
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                // View your learning progress and statistics
              </p>
            </CardContent>
          </Card>
        </Link>

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <BookOpen className="w-4 h-4" />
              // About Scripts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              // Learn about Japanese writing systems
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
