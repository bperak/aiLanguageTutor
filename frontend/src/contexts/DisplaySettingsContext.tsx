"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type DisplaySettings = {
  showKanji: boolean;
  showRomaji: boolean;
  showFurigana: boolean;
  showTranslation: boolean;
  level: number; // 1-6, affects default visibility
};

const defaultSettings: DisplaySettings = {
  showKanji: true,
  showRomaji: false,
  showFurigana: true,
  showTranslation: true,
  level: 3,
};

// Preset configurations based on level
export const levelPresets: Record<number, Partial<DisplaySettings>> = {
  1: { showRomaji: true, showFurigana: true, showTranslation: true }, // Beginner
  2: { showRomaji: true, showFurigana: true, showTranslation: true }, // Elementary
  3: { showRomaji: false, showFurigana: true, showTranslation: true }, // Intermediate
  4: { showRomaji: false, showFurigana: true, showTranslation: false }, // Upper-Int
  5: { showRomaji: false, showFurigana: false, showTranslation: false }, // Advanced
  6: { showRomaji: false, showFurigana: false, showTranslation: false }, // Proficient
};

type DisplaySettingsContextType = {
  settings: DisplaySettings;
  updateSettings: (updates: Partial<DisplaySettings>) => void;
  applyLevelPreset: (level: number) => void;
  resetToDefaults: () => void;
};

const DisplaySettingsContext = createContext<DisplaySettingsContextType | null>(
  null
);

export function DisplaySettingsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Always start with default settings to match server render
  const [settings, setSettings] = useState<DisplaySettings>(defaultSettings);

  // Load from localStorage after mount to prevent hydration mismatch
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("japaneseDisplaySettings");
      if (saved) {
        try {
          setSettings({ ...defaultSettings, ...JSON.parse(saved) });
        } catch (e) {
          // Invalid JSON, use defaults
          setSettings(defaultSettings);
        }
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("japaneseDisplaySettings", JSON.stringify(settings));
  }, [settings]);

  const updateSettings = (updates: Partial<DisplaySettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const applyLevelPreset = (level: number) => {
    const preset = levelPresets[level] || {};
    setSettings((prev) => ({ ...prev, ...preset, level }));
  };

  const resetToDefaults = () => {
    setSettings(defaultSettings);
  };

  return (
    <DisplaySettingsContext.Provider
      value={{ settings, updateSettings, applyLevelPreset, resetToDefaults }}
    >
      {children}
    </DisplaySettingsContext.Provider>
  );
}

export function useDisplaySettings() {
  const context = useContext(DisplaySettingsContext);
  if (!context) {
    throw new Error(
      "useDisplaySettings must be used within DisplaySettingsProvider"
    );
  }
  return context;
}
