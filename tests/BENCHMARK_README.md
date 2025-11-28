# AI Model Benchmark for Lesson Generation

## Overview

This benchmark suite tests different AI models (Gemini, OpenAI) for generating CanDo lessons, measuring:

- **Generation Time**: How long each model takes
- **Success Rate**: How reliably each model generates valid content  
- **Content Quality**: Whether generated content matches the topic (no generic templates)
- **Structure Validity**: Whether the generated JSON has the required structure

## Models Tested

1. **Gemini 2.5 Pro** - Google's latest model
2. **GPT-4o-mini** - OpenAI's fast model
3. **GPT-4o** - OpenAI's most capable model

## Test Cases

The benchmark generates lessons for:

1. **人との関係 (Relationships)** - A1 level, basic greetings
2. **食生活 (Food)** - A2 level, ordering food  
3. **買い物 (Shopping)** - B1 level, shopping for clothes

## Running the Benchmark

### Option 1: Quick Start (Recommended)

```powershell
.\scripts\run_model_benchmark.ps1
```

This interactive script lets you choose:
- Full benchmark (all models, all test cases)
- Quick test (single lesson, fastest)
- Pytest mode (detailed test output)

### Option 2: Run with Pytest

```bash
cd backend
poetry run pytest ../tests/test_lesson_generation_benchmark.py -v -s
```

**Single quick test:**
```bash
cd backend
poetry run pytest ../tests/test_lesson_generation_benchmark.py::test_single_lesson_quick -v -s
```

### Option 3: Standalone Script

```bash
cd backend
poetry run python ../scripts/benchmark_ai_models.py
```

## Output

The benchmark will display:

```
================================================================================
LESSON GENERATION BENCHMARK RESULTS
================================================================================

📚 Test Case: TEST:001 - 人との関係
   Description: Basic greetings and introductions
--------------------------------------------------------------------------------
   ✅ GPT-4o-mini            |  12.34s |  45.2KB | 7 sections | ✓ Valid | ✓ Topic-specific
   ✅ Gemini 2.5 Pro         |  28.56s |  52.1KB | 8 sections | ✓ Valid | ✓ Topic-specific
   ❌ GPT-4o                 |  35.01s | Error: Timeout

================================================================================
SUMMARY STATISTICS
================================================================================

📊 GPT-4o-mini
   Success Rate:    3/3 (100.0%)
   Avg Time:        14.23s
   Generic Content: 0/3 lessons

📊 Gemini 2.5 Pro
   Success Rate:    2/3 (66.7%)
   Avg Time:        29.45s
   Generic Content: 0/2 lessons

================================================================================
RECOMMENDATIONS
================================================================================

⚡ Fastest Model: GPT-4o-mini (14.23s avg)
🎯 Most Reliable: GPT-4o-mini (3/3 successful)
✨ Best Quality: GPT-4o-mini (no generic content, 14.23s)

💡 Suggested configuration: Use GPT-4o-mini for production
```

## Results File

Detailed results are saved to `tests/benchmark_results.json`:

```json
[
  {
    "success": true,
    "duration_seconds": 12.34,
    "error": null,
    "content_size": 46285,
    "has_generic_content": false,
    "has_valid_structure": true,
    "section_count": 7,
    "model": "gpt-4o-mini",
    "can_do_id": "TEST:001",
    "topic": "人との関係",
    "model_name": "GPT-4o-mini",
    "provider": "openai"
  }
]
```

## Interpreting Results

### Speed
- **Fast**: < 20 seconds
- **Medium**: 20-40 seconds  
- **Slow**: > 40 seconds

### Success Rate
- **Excellent**: 100% success
- **Good**: 80-99% success
- **Fair**: 60-79% success
- **Poor**: < 60% success

### Quality Indicators
- **✓ Topic-specific**: Content matches the lesson topic (GOOD)
- **⚠️ GENERIC**: Contains generic station/travel examples (BAD)
- **✓ Valid**: Has required JSON structure (GOOD)
- **✗ Invalid**: Missing required fields (BAD)

## Configuration

The timeout is set in `backend/app/core/config.py`:

```python
AI_REQUEST_TIMEOUT_SECONDS: int = Field(
    default=35, description="Timeout in seconds for AI generation requests"
)
```

To increase timeout for testing:
```python
AI_REQUEST_TIMEOUT_SECONDS: int = Field(default=60, ...)
```

## Troubleshooting

### "Timeout after 35 seconds"
- Model is too slow for the prompt
- Try increasing `AI_REQUEST_TIMEOUT_SECONDS`
- Consider using a faster model (GPT-4o-mini)

### "Invalid JSON"
- Model struggled with complex JSON schema
- The improved prompt should reduce this
- Check `errors` in benchmark_results.json

### "Generic Content Detected"
- Model used template content instead of topic-specific
- Validation is working correctly (rejecting bad content)
- Try different model or simplify prompt

## Next Steps

Based on benchmark results:

1. **Update configuration** to use the fastest reliable model:
   ```python
   # In backend/app/services/cando_lesson_session_service.py
   provider="openai" if provider == "openai" else "gemini"
   model=("gpt-4o-mini" if provider == "openai" else "gemini-2.5-pro")
   ```

2. **Adjust timeout** based on slowest acceptable model:
   ```python
   AI_REQUEST_TIMEOUT_SECONDS = 45  # If GPT-4o-mini averages 15s
   ```

3. **Set default provider** in endpoint:
   ```python
   provider = settings.DEFAULT_AI_PROVIDER or "openai"
   ```

## Adding New Test Cases

Edit `tests/test_lesson_generation_benchmark.py`:

```python
self.test_cases = [
    {
        "can_do_id": "TEST:004",
        "topic": "旅行と交通",  # Your topic
        "level": "A2",
        "description": "Asking for directions"
    }
]
```

## Adding New Models

Edit the `models` list:

```python
self.models = [
    {"name": "Claude 3.5 Sonnet", "provider": "anthropic", "model": "claude-3-5-sonnet"},
]
```

(Requires implementing provider support in `ai_chat_service.py`)

