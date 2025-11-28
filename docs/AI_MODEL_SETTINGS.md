# AI Model Settings

## Overview

The AI Language Tutor supports multiple AI models from OpenAI and Google Gemini for lesson generation. Users can customize which model to use and adjust timeout settings based on their needs.

## Available Models

### OpenAI Models

| Model | Description | Speed | Best For |
|-------|-------------|-------|----------|
| **GPT-5** | 🌟 Next-generation model | Medium | Most advanced lessons, latest capabilities |
| **GPT-5 Mini** | ⚡ Fast next-gen model | Fast | Quick, efficient lessons |
| **GPT-4.1** | 🚀 1M context, best JSON | Medium | Complex multilingual lessons, structured output |
| **GPT-4o** | 🏆 Excellent multilingual | Medium | Balanced quality and speed |
| **GPT-4o Mini** | ⚡ Fastest and cheapest | Fast | Quick iterations, cost-effective |
| **GPT-4 Turbo** | ⚙️ Balanced option | Medium | General-purpose lessons |
| **O1 Preview** | 🧠 Extended reasoning | Slow | Complex reasoning tasks |
| **O1 Mini** | 💡 Fast reasoning | Fast | Balanced reasoning and speed |

### Gemini Models

| Model | Description | Speed | Best For |
|-------|-------------|-------|----------|
| **Gemini 2.5 Flash** ⭐ | ⚡ Fast balanced | Fast | Recommended default, best balance |
| **Gemini 2.0 Flash Exp** | 💨 Fastest experimental | Fastest | Rapid prototyping |
| **Gemini 2.0 Flash Thinking** | 🧠 With reasoning | Medium | Lessons requiring logic |
| **Gemini 1.5 Pro** | 📊 Balanced | Medium | Stable, reliable lessons |
| **Gemini 1.5 Flash** | 💨 Fast efficient | Fast | Quick generation |
| **Gemini 2.5 Pro** | 🎯 Most capable | Slow | Highest quality, complex lessons |

## Configuring Models

### Via Settings Page

1. Navigate to **Settings** (⚙️ in main menu)
2. Select **AI Provider** (OpenAI or Gemini)
3. Choose your preferred **Model**
4. Adjust **Timeout** slider (60s - 300s)
5. Settings are saved automatically to your browser

### Timeout Settings

- **Minimum**: 60 seconds
- **Default**: 90 seconds
- **Maximum**: 300 seconds (5 minutes)

**Recommendations:**
- **60-90s**: Fast models (GPT-4o-mini, Gemini Flash)
- **90-120s**: Standard lessons
- **120-180s**: Complex multilingual lessons
- **180-300s**: Very detailed lessons or slower models

## How Model Selection Works

1. **User selects model** in Settings
2. Settings are **stored in browser localStorage**
3. When starting a lesson:
   - Frontend reads settings from localStorage
   - Settings are sent as query parameters to backend
   - Backend validates and caps timeout
   - Selected model is used for generation

## Troubleshooting

### Timeout Errors

**Error**: `Gemini API request timed out after 90 seconds`

**Solutions:**
1. Increase timeout in Settings (120-180s recommended)
2. Switch to a faster model:
   - OpenAI: GPT-4o-mini, GPT-4o
   - Gemini: Gemini 2.5 Flash, Gemini 2.0 Flash Exp
3. Simplify lesson complexity if possible

### Model Not Available

**Error**: `Model not found` or `Invalid model`

**Solutions:**
1. Check that API keys are configured in backend `.env`
2. Verify model ID matches available models
3. Try switching to a different provider

### Generation Quality Issues

**Problem**: Generic or low-quality content

**Solutions:**
1. Try premium models:
   - OpenAI: GPT-5, GPT-4.1
   - Gemini: Gemini 2.5 Pro
2. Increase timeout to allow more processing time
3. Regenerate lesson (models use randomness)

## API Reference

### Endpoints

#### GET `/api/v1/cando/ai-models`

Returns available models and current configuration.

**Response:**
```json
{
  "providers": {
    "openai": {
      "name": "OpenAI",
      "icon": "🤖",
      "models": [...]
    },
    "gemini": {...}
  },
  "timeout": {
    "default": 90,
    "min": 60,
    "max": 300
  },
  "current": {
    "provider": "openai",
    "model": "gpt-4o",
    "timeout": 90
  }
}
```

#### POST `/api/v1/cando/lessons/start`

Starts a lesson with optional model override.

**Query Parameters:**
- `can_do_id`: CanDo descriptor ID (required)
- `level`: Learner level 1-6 (optional)
- `provider`: AI provider (openai|gemini) (optional)
- `model`: Model ID (optional)
- `timeout`: Timeout in seconds (optional, capped to max)

## Best Practices

### For Teachers

1. **Test with multiple models** to find the best fit for your content
2. **Use faster models** for prototyping
3. **Switch to premium models** for final, approved lessons
4. **Document which model** produced the best results for each topic

### For Developers

1. **Always provide fallback** to default model if custom fails
2. **Log model and timeout** for debugging
3. **Monitor timeout errors** by model to identify issues
4. **Validate settings** server-side (never trust client)

### For Students

1. **Default settings work well** for most lessons
2. **If lesson times out**, try:
   - Increasing timeout
   - Switching to faster model
3. **Quality may vary** between generations (regenerate if needed)

## Performance Comparison

Based on internal testing for Japanese lesson generation:

| Model | Avg Time | Success Rate | Quality | Size | Cost |
|-------|----------|--------------|---------|------|------|
| GPT-5 | TBD | TBD | TBD | TBD | High |
| GPT-4.1 | 45s | 95% | ⭐⭐⭐⭐⭐ | 12KB | High |
| GPT-4o | 35s | 98% | ⭐⭐⭐⭐ | 10KB | Medium |
| GPT-4o-mini | 20s | 99% | ⭐⭐⭐ | 8KB | Low |
| Gemini 2.5 Flash | 25s | 97% | ⭐⭐⭐⭐ | 9KB | Low |
| Gemini 2.5 Pro | 60s | 95% | ⭐⭐⭐⭐⭐ | 13KB | Medium |

*Note: Times vary based on lesson complexity and server load*

## Future Enhancements

- [ ] Custom model providers (user-added APIs)
- [ ] Per-topic model recommendations
- [ ] Automatic model selection based on topic complexity
- [ ] Model performance analytics dashboard
- [ ] A/B testing different models
- [ ] Cost tracking per model

## Related Documentation

- [TEACHER_APPROVAL_SYSTEM.md](../TEACHER_APPROVAL_SYSTEM.md) - Saving and approving lessons
- [MULTILINGUAL_DISPLAY_SYSTEM.md](../MULTILINGUAL_DISPLAY_SYSTEM.md) - Display settings
- [LESSON_SERVICE_ARCHITECTURE.md](./LESSON_SERVICE_ARCHITECTURE.md) - Technical architecture

