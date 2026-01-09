"use client";
import React from "react";
import { AIModelSettings } from "@/components/settings/AIModelSettings";
import { DisplaySettingsPanel } from "@/components/settings/DisplaySettingsPanel";
export default function SettingsPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>{" "}
        <p className="text-muted-foreground mt-2">
          // Configure AI models, display preferences, and other options
        </p>
      </div>{" "}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI Model Settings */}{" "}
        <div>
          <AIModelSettings />
        </div>{" "}
        {/* Display Settings */}{" "}
        <div>
          <DisplaySettingsPanel />
        </div>
      </div>{" "}
      {/* Profile Building Section */}{" "}
      <div className="mt-8">
        <div className="p-6 bg-muted rounded-lg border border-border">
          <h2 className="text-lg font-semibold text-foreground mb-2">
            Profile & Learning Path
          </h2>{" "}
          <p className="text-sm text-muted-foreground mb-4">
            // Build your learning profile to get personalized recommendations and
            // a custom learning path.
          </p>{" "}
          <a
            href="/profile/build"
            className="inline-block px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            // Build or Update Profile
          </a>
        </div>
      </div>{" "}
      {/* Help Section */}{" "}
      <div className="mt-8 p-6 bg-blue-500/10 rounded-lg border border-blue-500/30 ">
        <h2 className="text-lg font-semibold text-blue-700 text-blue-700 mb-2">
          💡 Tips
        </h2>{" "}
        <ul className="text-sm text-blue-600 space-y-1">
          <li>
            • <strong>GPT-5</strong> and <strong>GPT-4.1</strong> are
            // recommended for complex multilingual lessons
          </li>{" "}
          <li>
            • <strong>Gemini 2.5 Flash</strong> offers the best balance of speed
            // and quality
          </li>{" "}
          <li>• Increase timeout to 120-180s for very complex lessons</li>{" "}
          <li>• Settings are saved automatically to your browser</li>
        </ul>
      </div>
    </div>
  );
}
