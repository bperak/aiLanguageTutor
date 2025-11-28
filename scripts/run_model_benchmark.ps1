# PowerShell script to run AI model benchmark
# Usage: .\scripts\run_model_benchmark.ps1

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   AI Model Benchmark Test Suite" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

Write-Host "📍 Changing to backend directory..." -ForegroundColor Yellow
Set-Location backend

Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
} else {
    Write-Host "⚠️  Virtual environment not found. Installing dependencies..." -ForegroundColor Yellow
    poetry install
}

Write-Host "`n🚀 Running benchmark...`n" -ForegroundColor Green

# Option 1: Run as pytest (more detailed output)
Write-Host "Option 1: Run with pytest (detailed test output)" -ForegroundColor Cyan
Write-Host "Command: poetry run pytest ../tests/test_lesson_generation_benchmark.py::test_benchmark_lesson_generation -v -s`n" -ForegroundColor Gray

# Option 2: Run as standalone script (cleaner output)
Write-Host "Option 2: Run standalone (cleaner output)" -ForegroundColor Cyan
Write-Host "Command: poetry run python ../scripts/benchmark_ai_models.py`n" -ForegroundColor Gray

# Option 3: Quick test (single lesson)
Write-Host "Option 3: Quick test (single lesson, fast)" -ForegroundColor Cyan
Write-Host "Command: poetry run pytest ../tests/test_lesson_generation_benchmark.py::test_single_lesson_quick -v -s`n" -ForegroundColor Gray

$choice = Read-Host "Choose option (1/2/3) or press Enter for option 2"

switch ($choice) {
    "1" {
        Write-Host "`n📊 Running pytest benchmark...`n" -ForegroundColor Green
        poetry run pytest ../tests/test_lesson_generation_benchmark.py::test_benchmark_lesson_generation -v -s
    }
    "3" {
        Write-Host "`n⚡ Running quick test...`n" -ForegroundColor Green
        poetry run pytest ../tests/test_lesson_generation_benchmark.py::test_single_lesson_quick -v -s
    }
    default {
        Write-Host "`n🎯 Running standalone benchmark...`n" -ForegroundColor Green
        poetry run python ../scripts/benchmark_ai_models.py
    }
}

Write-Host "`n✅ Benchmark complete!" -ForegroundColor Green
Write-Host "📁 Results saved to: tests/benchmark_results.json`n" -ForegroundColor Cyan

# Return to root directory
Set-Location ..

Read-Host "Press Enter to exit"

