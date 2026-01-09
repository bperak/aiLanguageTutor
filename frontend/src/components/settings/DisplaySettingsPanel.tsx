"use client";

import React from "react";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function DisplaySettingsPanel() {
  const { settings, updateSettings, applyLevelPreset, resetToDefaults } =
    useDisplaySettings();

  const toggleOptions = [
    {
      key: "showKanji" as const,
      label: "📝 Standard Orthography (Kanji)",
      description: "Show Japanese text with kanji characters",
    },
    {
      key: "showFurigana" as const,
      label: "🔤 Furigana (Ruby Text)",
      description: "Show pronunciation guides above kanji",
    },
    {
      key: "showRomaji" as const,
      label: "🔡 Romaji (Romanization)",
      description: "Show romanized Japanese (abc)",
    },
    {
      key: "showTranslation" as const,
      label: "🌐 English Translation",
      description: "Show English translations",
    },
  ];

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Japanese Display Settings</CardTitle>
        <CardDescription>
          Customize how Japanese text is displayed throughout lessons
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Level Presets */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            Quick Presets by Level
          </label>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {[1, 2, 3, 4, 5, 6].map((level) => (
              <button
                key={level}
                onClick={() => applyLevelPreset(level)}
                className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                  settings.level === level
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted hover:bg-accent text-muted-foreground"
                }`}
              >
                Level {level}
              </button>
            ))}
          </div>
        </div>

        {/* Individual Toggles */}
        <div className="space-y-3">
          {toggleOptions.map(({ key, label, description }) => (
            <label
              key={key}
              className="flex items-start gap-3 cursor-pointer group"
            >
              <input
                type="checkbox"
                checked={settings[key]}
                onChange={(e) => updateSettings({ [key]: e.target.checked })}
                className="mt-1 w-5 h-5 rounded border-input text-primary focus:ring-ring"
              />
              <div className="flex-1">
                <div className="font-medium text-sm group-hover:text-primary transition-colors">
                  {label}
                </div>
                <div className="text-xs text-muted-foreground">
                  {description}
                </div>
              </div>
            </label>
          ))}
        </div>

        {/* Reset Button */}
        <button
          onClick={resetToDefaults}
          className="w-full px-4 py-2 text-sm text-muted-foreground border border-input rounded hover:bg-accent"
        >
          Reset to Defaults
        </button>
      </CardContent>
    </Card>
  );
}
