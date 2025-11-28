# PowerShell script to run RAG end-to-end tests

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RAG Implementation Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "Checking backend status..." -ForegroundColor Yellow
$backendHealth = try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get -ErrorAction Stop
    $true
} catch {
    $false
}

if (-not $backendHealth) {
    Write-Host "ERROR: Backend is not running on http://localhost:8000" -ForegroundColor Red
    Write-Host "Please start the backend first: docker-compose up backend" -ForegroundColor Yellow
    exit 1
}

Write-Host "Backend is healthy!" -ForegroundColor Green
Write-Host ""

# Step 1: Run migration if needed
Write-Host "Step 1: Checking database schema..." -ForegroundColor Yellow
Write-Host "Note: If migration hasn't been run, you may need to run it manually:" -ForegroundColor Yellow
Write-Host "  docker exec -i ai-tutor-postgres psql -U postgres -d ai_language_tutor < backend/migrations/2025-11-06_enrich_chat_sessions_pgvector.sql" -ForegroundColor Cyan
Write-Host ""

# Step 2: Run tests
Write-Host "Step 2: Running end-to-end tests..." -ForegroundColor Yellow
Write-Host ""

cd backend
poetry run python tests/test_rag_phases_end_to_end.py

$testExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($testExitCode -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed. Check output above." -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan

exit $testExitCode

