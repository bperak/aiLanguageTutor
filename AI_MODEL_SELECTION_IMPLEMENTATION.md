# AI Model Selection & Timeout Settings - Implementation Summary

## Overview

Successfully implemented a comprehensive AI model selection system with timeout controls, allowing users to choose between multiple OpenAI and Gemini models for lesson generation. This addresses timeout issues and gives users full control over AI generation parameters.

## What Was Implemented

### Backend Changes

#### 1. Configuration (`backend/app/core/config.py`)

Added comprehensive model lists and timeout configurations:

- **OpenAI Models**: GPT-5, GPT-5 Mini, GPT-4.1, GPT-4o, GPT-4o-mini, GPT-4 Turbo, O1 Preview, O1 Mini
- **Gemini Models**: Gemini 2.5 Flash, Gemini 2.0 Flash Exp, Gemini 2.0 Flash Thinking, Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.5 Pro
- **Timeout Settings**: Min 60s, Default 90s, Max 300s (5 minutes)
- **Smart Defaults**: GPT-4o for OpenAI, Gemini 2.5 Flash for Gemini

#### 2. API Endpoints (`backend/app/api/v1/endpoints/cando.py`)

**New Endpoint: GET `/api/v1/cando/ai-models`**
- Returns available models grouped by provider
- Includes timeout configuration and current defaults
- Provides model metadata (name, description, speed, recommendation)

**Updated Endpoint: POST `/api/v1/cando/lessons/start`**
- Accepts optional `provider`, `model`, and `timeout` query parameters
- Validates and caps timeout to configured limits
- Passes parameters through to service layer

#### 3. Service Layer (`backend/app/services/cando_lesson_session_service.py`)

**Updated `start_lesson` method:**
- Accepts `model` and `timeout` parameters
- Implements smart model selection based on provider
- Logs all AI generation parameters for debugging

**Updated `_generate_master_lesson` method:**
- Accepts `model` and `timeout` parameters
- Passes them directly to AI chat service
- Uses exact model specified (no hardcoding)

### Frontend Changes

#### 1. Settings Component (`frontend/src/components/settings/AIModelSettings.tsx`)

New React component featuring:
- **Provider Selection**: Toggle between OpenAI and Gemini
- **Model Grid**: Radio buttons with descriptions and speed indicators
- **Timeout Slider**: 60-300s range with visual feedback
- **Configuration Summary**: Shows current settings at bottom
- **Auto-save**: Settings persist to localStorage automatically

#### 2. Settings Page (`frontend/src/app/settings/page.tsx`)

New dedicated settings page:
- Side-by-side layout for AI Model Settings and Display Settings
- Tips section with model recommendations
- Clean, organized interface
- Accessible via main navigation

#### 3. Navigation (`frontend/src/components/NavBar.tsx`)

Added Settings link:
- Prominent placement in main menu (⚙️ Settings)
- Available on both desktop and mobile
- Easy access from anywhere in the app

#### 4. Lesson Page Integration (`frontend/src/app/cando/[canDoId]/page.tsx`)

Enhanced lesson generation:
- Reads AI model settings from localStorage
- Passes settings as query parameters to backend
- Shows current model in loading messages
- Displays model indicator badge on lesson page
- "Change" link for quick access to settings
- Custom timeout adapts to user preferences

### Documentation

Created comprehensive documentation (`docs/AI_MODEL_SETTINGS.md`):
- Model comparison table
- Timeout recommendations
- Troubleshooting guide
- API reference
- Best practices for teachers, developers, and students
- Performance benchmarks

## Features

### User Features

✅ **Model Selection**
- Choose from 8 OpenAI models
- Choose from 6 Gemini models
- Clear descriptions and speed indicators
- Recommended models highlighted

✅ **Timeout Control**
- Adjustable 60-300s timeout
- Visual slider interface
- Clear warnings about wait times

✅ **Settings Persistence**
- Automatic save to browser localStorage
- Settings persist across sessions
- No login required for preferences

✅ **UI Integration**
- Settings accessible from main menu
- Model indicator on lesson page
- Quick "Change" link for easy adjustment
- Loading messages show which model is being used

✅ **Error Handling**
- Clear timeout error messages
- Suggestions for resolution
- Model and timeout info in error messages

### Technical Features

✅ **Smart Defaults**
- Provider-specific default models
- Fallback to config if not specified
- Validation and capping of timeout values

✅ **Logging**
- All AI parameters logged for debugging
- Provider, model, timeout visible in logs
- Easy troubleshooting

✅ **Flexible Architecture**
- Easy to add new models
- Provider-agnostic design
- Backend validation of client settings

## Testing Recommendations

### Critical Test Scenarios

1. **Model Switching**
   - [ ] Change from OpenAI to Gemini in Settings
   - [ ] Verify model indicator updates on lesson page
   - [ ] Generate lesson with each provider
   - [ ] Confirm correct model is used (check backend logs)

2. **Timeout Adjustment**
   - [ ] Set timeout to 60s
   - [ ] Set timeout to 180s
   - [ ] Set timeout to 300s
   - [ ] Verify timeout is respected (check error timing)

3. **Model-Specific Generation**
   - [ ] Test GPT-5 (when available)
   - [ ] Test GPT-4.1
   - [ ] Test GPT-4o-mini
   - [ ] Test Gemini 2.5 Flash
   - [ ] Test Gemini 2.5 Pro
   - [ ] Compare quality and speed

4. **Settings Persistence**
   - [ ] Set model to GPT-4o
   - [ ] Reload page
   - [ ] Verify setting persists
   - [ ] Close and reopen browser
   - [ ] Verify setting still persists

5. **Error Scenarios**
   - [ ] Set very low timeout (60s) with slow model
   - [ ] Verify timeout error message includes model info
   - [ ] Verify "Try increasing timeout" suggestion appears
   - [ ] Test recovery by increasing timeout

6. **UI/UX**
   - [ ] Settings page loads correctly
   - [ ] Model list displays properly
   - [ ] Timeout slider works smoothly
   - [ ] Configuration summary updates
   - [ ] Mobile navigation includes Settings
   - [ ] Model indicator appears on lesson page
   - [ ] "Change" link navigates to Settings

## Files Modified

### Backend
- `backend/app/core/config.py` - Model lists and timeout config
- `backend/app/api/v1/endpoints/cando.py` - New endpoint and parameter handling
- `backend/app/services/cando_lesson_session_service.py` - Model and timeout support

### Frontend
- `frontend/src/components/settings/AIModelSettings.tsx` - New component
- `frontend/src/app/settings/page.tsx` - New page
- `frontend/src/components/NavBar.tsx` - Added Settings link
- `frontend/src/app/cando/[canDoId]/page.tsx` - Settings integration

### Documentation
- `docs/AI_MODEL_SETTINGS.md` - New comprehensive guide
- `AI_MODEL_SELECTION_IMPLEMENTATION.md` - This summary

## Benefits

### For Users
- **Resolves Timeout Issues**: Can switch to faster models or increase timeout
- **Cost Control**: Choose cheaper models for practice
- **Quality Control**: Use premium models for important lessons
- **Flexibility**: Adjust settings per-lesson as needed

### For Teachers
- **Experimentation**: Test multiple models to find best fit
- **Optimization**: Balance speed and quality
- **Documentation**: Know which model produced which lesson

### For Developers
- **Maintainability**: Easy to add new models
- **Debugging**: Full parameter logging
- **Flexibility**: Provider-agnostic design

## Next Steps (Future Enhancements)

1. **Custom Providers** - Allow users to add their own API keys and models
2. **Model Analytics** - Track performance metrics per model
3. **Auto-Selection** - AI recommends best model based on topic/complexity
4. **Cost Tracking** - Show estimated costs per model
5. **A/B Testing** - Compare multiple models for same lesson
6. **Model History** - Track which models were used for each lesson

## Known Limitations

1. **GPT-5 availability** - Included in anticipation of release, may not be immediately available
2. **Browser-only persistence** - Settings not synced across devices (future: user profiles)
3. **No cost display** - Users don't see actual API costs (future: analytics)
4. **Manual testing** - Need to manually verify models work (future: automated tests)

## Support

For issues or questions:
1. Check `docs/AI_MODEL_SETTINGS.md` for troubleshooting
2. Review backend logs for generation errors
3. Test with different models/timeouts
4. Report persistent issues with model name and timeout used

---

**Implementation Date**: January 2025  
**Status**: ✅ Complete and Ready for Testing  
**Backend Restart Required**: Yes (completed)

