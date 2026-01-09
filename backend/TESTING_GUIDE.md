# User Path Module - Testing Guide

## ✅ What We've Verified

### Code Structure ✓
- All 4 service files compile without syntax errors
- All 3 test files have correct structure
- 18 test functions properly defined
- All imports and dependencies are correctly specified

### Integration Points ✓
- `LearningPathService` integrates with `UserPathService`
- API endpoints return full path data
- Configuration settings are defined
- Singleton instances properly created

### Test Files Created ✓
1. **test_user_path_service.py** - 8 test functions
2. **test_path_builder.py** - 5 test functions  
3. **test_cando_complexity_service.py** - 5 test functions

## 🚀 Running the Tests

### Option 1: Using the Test Runner Script

```bash
cd /root/aiLanguageTutor/backend
python3 run_path_module_tests.py
```

The script will:
- Load environment variables from `/root/aiLanguageTutor/.env`
- Check for required dependencies
- Run all test files
- Provide clear output

### Option 2: Using pytest Directly

```bash
cd /root/aiLanguageTutor/backend

# Run all path module tests
pytest tests/services/test_user_path_service.py tests/services/test_path_builder.py tests/services/test_cando_complexity_service.py -v

# Run specific test file
pytest tests/services/test_user_path_service.py -v

# Run specific test
pytest tests/services/test_cando_complexity_service.py::test_map_level_to_numeric -v

# Run with coverage
pytest tests/services/ --cov=app.services.user_path_service --cov=app.services.path_builder --cov=app.services.cando_complexity_service --cov=app.services.cando_selector_service -v
```

### Option 3: Using Poetry (if available)

```bash
cd /root/aiLanguageTutor/backend
poetry install  # Install dependencies
poetry run pytest tests/services/ -v
```

## 📋 Required Dependencies

The tests require these packages (already in `pyproject.toml`):
- `pytest ^7.4.3`
- `pytest-asyncio ^0.21.1`
- `pytest-cov ^4.1.0`
- `structlog ^23.2.0`
- `pydantic ^2.5.0`
- And other app dependencies

## 🔧 Environment Setup

The test runner automatically loads environment variables from:
- `/root/aiLanguageTutor/.env`

Make sure your `.env` file contains:
- Database connection strings (PostgreSQL, Neo4j)
- AI API keys (OpenAI, Gemini)
- Other required configuration

## 📊 Test Coverage

### test_user_path_service.py
- ✓ Profile analysis
- ✓ Path generation (with/without CanDo descriptors)
- ✓ Helper methods (level mapping, path naming, etc.)

### test_path_builder.py
- ✓ Semantic path building algorithm
- ✓ Finding next related CanDo descriptors
- ✓ Path continuity verification

### test_cando_complexity_service.py
- ✓ CEFR level to numeric mapping
- ✓ AI-based complexity assessment
- ✓ Complexity comparison and ranking

## 🐛 Troubleshooting

### Issue: "No module named pytest"
**Solution:** Install dependencies:
```bash
pip install pytest pytest-asyncio
# or
poetry install
```

### Issue: "ModuleNotFoundError: No module named 'structlog'"
**Solution:** Install app dependencies:
```bash
pip install -r requirements.txt
# or
poetry install
```

### Issue: Tests fail with database connection errors
**Solution:** Ensure:
- PostgreSQL is running and accessible
- Neo4j is running and accessible
- Connection strings in `.env` are correct

### Issue: Tests fail with AI API errors
**Solution:** Ensure:
- API keys are set in `.env`
- API keys are valid
- Network connectivity to AI services

## 📝 Test Results

When tests run successfully, you should see output like:

```
tests/services/test_user_path_service.py::test_analyze_profile_for_path PASSED
tests/services/test_user_path_service.py::test_generate_user_path_success PASSED
tests/services/test_path_builder.py::test_build_semantic_path PASSED
tests/services/test_cando_complexity_service.py::test_assess_complexity_success PASSED
...
======================== 18 passed in X.XXs ========================
```

## ✨ Next Steps

1. **Install dependencies** (if not already installed)
2. **Verify .env file** is in the correct location
3. **Run the test suite** using one of the methods above
4. **Review test output** for any failures
5. **Fix any issues** and re-run tests

## 📚 Additional Resources

- Test files: `tests/services/`
- Service files: `app/services/`
- Configuration: `app/core/config.py`
- Test runner: `run_path_module_tests.py`

---

**Status:** All code structure verified ✓  
**Ready for:** Runtime testing when dependencies are installed

