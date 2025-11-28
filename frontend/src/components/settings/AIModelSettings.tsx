"use client"

import React, { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { apiGet } from "@/lib/api"

type ModelInfo = {
  id: string
  name: string
  description: string
  recommended?: boolean
  speed: string
}

type ProviderInfo = {
  name: string
  icon: string
  models: ModelInfo[]
}

type AIModelSettings = {
  provider: string
  model: string
  timeout: number
}

export function AIModelSettings() {
  const [availableModels, setAvailableModels] = useState<any>(null)
  const [settings, setSettings] = useState<AIModelSettings>({
    provider: "openai",
    model: "gpt-4o",
    timeout: 90
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Load from API
    apiGet("/api/v1/cando/ai-models")
      .then(data => {
        setAvailableModels(data)
        // Load from localStorage or use API defaults
        const saved = localStorage.getItem('aiModelSettings')
        if (saved) {
          setSettings(JSON.parse(saved))
        } else {
          setSettings({
            provider: data.current.provider,
            model: data.current.model,
            timeout: data.timeout.default
          })
        }
        setLoading(false)
      })
      .catch(err => {
        console.error("Failed to load models:", err)
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    // Persist to localStorage
    localStorage.setItem('aiModelSettings', JSON.stringify(settings))
  }, [settings])

  if (loading || !availableModels) {
    return <div className="text-sm text-gray-500">Loading AI models...</div>
  }

  const currentProvider: ProviderInfo = availableModels.providers[settings.provider]
  const speedIcons = { fastest: "🚀", fast: "⚡", medium: "⚙️", slow: "🐢" }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>AI Model Settings</CardTitle>
        <CardDescription>
          Choose which AI model to use for lesson generation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Provider Selection */}
        <div>
          <label className="text-sm font-medium mb-2 block">AI Provider</label>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(availableModels.providers).map(([key, provider]: [string, any]) => (
              <button
                key={key}
                onClick={() => {
                  const firstModel = provider.models.find((m: ModelInfo) => m.recommended) || provider.models[0]
                  setSettings(prev => ({ 
                    ...prev, 
                    provider: key, 
                    model: firstModel.id 
                  }))
                }}
                className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  settings.provider === key
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                <div className="text-2xl mb-1">{provider.icon}</div>
                {provider.name}
              </button>
            ))}
          </div>
        </div>

        {/* Model Selection */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            Model ({currentProvider.models.length} available)
          </label>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {currentProvider.models.map((model: ModelInfo) => (
              <label 
                key={model.id}
                className={`flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  settings.model === model.id
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="model"
                  checked={settings.model === model.id}
                  onChange={() => setSettings(prev => ({ ...prev, model: model.id }))}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="font-medium text-sm flex items-center gap-2 flex-wrap">
                    {model.name}
                    {model.recommended && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full font-medium">
                        ⭐ Recommended
                      </span>
                    )}
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
                      {speedIcons[model.speed as keyof typeof speedIcons]} {model.speed}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 mt-1">{model.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Timeout Slider */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            Request Timeout: <strong>{settings.timeout}s</strong>
          </label>
          <input
            type="range"
            min={availableModels.timeout.min}
            max={availableModels.timeout.max}
            step={30}
            value={settings.timeout}
            onChange={(e) => setSettings(prev => ({ ...prev, timeout: parseInt(e.target.value) }))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>⚡ {availableModels.timeout.min}s</span>
            <span>⏱️ {availableModels.timeout.max}s</span>
          </div>
          <div className="text-xs text-amber-600 mt-2 flex items-start gap-1">
            <span>⚠️</span>
            <span>Higher timeouts allow more complex lessons but increase wait time</span>
          </div>
        </div>

        {/* Current Selection Summary */}
        <div className="pt-4 border-t bg-blue-50 -mx-6 -mb-6 px-6 py-4 rounded-b-lg">
          <div className="text-sm font-medium text-blue-900 mb-1">Current Configuration:</div>
          <div className="text-sm text-blue-800">
            {currentProvider.icon} {currentProvider.name} • {
              currentProvider.models.find((m: ModelInfo) => m.id === settings.model)?.name
            } • {settings.timeout}s timeout
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

