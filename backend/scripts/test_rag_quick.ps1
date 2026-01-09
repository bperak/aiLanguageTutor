# Quick RAG test script using direct SQL queries

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RAG Quick Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test Phase 1: Database Schema
Write-Host "Phase 1: Testing Database Schema..." -ForegroundColor Yellow

$textsearchCheck = docker exec ai-tutor-postgres psql -U postgres -d ai_language_tutor -t -c "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversation_messages' AND column_name = 'textsearch');" 2>&1
$textsearchCheck = $textsearchCheck.Trim()

if ($textsearchCheck -eq "t") {
    Write-Host "  [PASS] textsearch column exists" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] textsearch column missing" -ForegroundColor Red
    Write-Host "  Run migration: docker exec -i ai-tutor-postgres psql -U postgres -d ai_language_tutor < backend/migrations/2025-11-06_enrich_chat_sessions_pgvector.sql" -ForegroundColor Yellow
}

$indexCheck = docker exec ai-tutor-postgres psql -U postgres -d ai_language_tutor -t -c "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'conversation_messages' AND indexname = 'idx_conversation_messages_textsearch');" 2>&1
$indexCheck = $indexCheck.Trim()

if ($indexCheck -eq "t") {
    Write-Host "  [PASS] textsearch index exists" -ForegroundColor Green
} else {
    Write-Host "  [WARN] textsearch index missing" -ForegroundColor Yellow
}

$vectorIndexCheck = docker exec ai-tutor-postgres psql -U postgres -d ai_language_tutor -t -c "SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'conversation_messages' AND indexname LIKE '%embedding%';" 2>&1
$vectorIndexCheck = $vectorIndexCheck.Trim()

if ([int]$vectorIndexCheck -gt 0) {
    Write-Host "  [PASS] Vector index(es) exist" -ForegroundColor Green
} else {
    Write-Host "  [WARN] No vector indexes found" -ForegroundColor Yellow
}

Write-Host ""

# Test Phase 2: Check for embeddings
Write-Host "Phase 2: Checking Embeddings..." -ForegroundColor Yellow

$embeddingCount = docker exec ai-tutor-postgres psql -U postgres -d ai_language_tutor -t -c "SELECT COUNT(*) FROM conversation_messages WHERE content_embedding IS NOT NULL;" 2>&1
$embeddingCount = $embeddingCount.Trim()

if ([int]$embeddingCount -gt 0) {
    Write-Host "  [PASS] Found $embeddingCount messages with embeddings" -ForegroundColor Green
} else {
    Write-Host "  [INFO] No embeddings found yet (create messages to generate embeddings)" -ForegroundColor Cyan
}

Write-Host ""

# Test Phase 3: Check search capability
Write-Host "Phase 3: Checking Search Capability..." -ForegroundColor Yellow

$searchableCount = docker exec ai-tutor-postgres psql -U postgres -d ai_language_tutor -t -c "SELECT COUNT(*) FROM conversation_messages m JOIN conversation_sessions s ON m.session_id = s.id WHERE m.content_embedding IS NOT NULL AND m.role = 'user';" 2>&1
$searchableCount = $searchableCount.Trim()

if ([int]$searchableCount -gt 0) {
    Write-Host "  [PASS] Found $searchableCount searchable messages" -ForegroundColor Green
} else {
    Write-Host "  [INFO] No searchable messages yet" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan





