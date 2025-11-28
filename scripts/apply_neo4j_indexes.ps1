# ================================================
# Neo4j Index Application Script for PowerShell
# ================================================

Write-Host "🔧 Neo4j Performance Index Application" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check if Neo4j is running
Write-Host "📊 Checking Neo4j status..." -ForegroundColor Yellow

try {
    # Try to connect to Neo4j and check if it's running
    $neo4jStatus = Invoke-RestMethod -Uri "http://localhost:7474/browser/" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Neo4j is running on port 7474" -ForegroundColor Green
} catch {
    Write-Host "❌ Neo4j is not accessible on port 7474" -ForegroundColor Red
    Write-Host "   Please ensure Neo4j is running and accessible" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📋 Instructions for applying indexes:" -ForegroundColor Yellow
Write-Host "1. Open Neo4j Browser at: http://localhost:7474" -ForegroundColor White
Write-Host "2. Login with your credentials" -ForegroundColor White
Write-Host "3. Copy and paste the contents of 'scripts/apply_indexes_direct.cypher'" -ForegroundColor White
Write-Host "4. Execute the script to create all indexes" -ForegroundColor White
Write-Host ""

# Check if the cypher file exists
$cypherFile = "scripts/apply_indexes_direct.cypher"
if (Test-Path $cypherFile) {
    Write-Host "📄 Cypher script found at: $cypherFile" -ForegroundColor Green
    Write-Host "   Content preview:" -ForegroundColor Yellow
    Write-Host "   " -NoNewline
    Get-Content $cypherFile | Select-Object -First 5 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
    Write-Host "   ... (see full file for complete script)" -ForegroundColor Gray
} else {
    Write-Host "❌ Cypher script not found at: $cypherFile" -ForegroundColor Red
}

Write-Host ""
Write-Host "🚀 Alternative: Use cypher-shell if available" -ForegroundColor Yellow

# Check if cypher-shell is available
try {
    $cypherVersion = cypher-shell --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ cypher-shell is available" -ForegroundColor Green
        Write-Host "   You can run: cypher-shell -u neo4j -p your_password -f scripts/apply_indexes_direct.cypher" -ForegroundColor White
    }
} catch {
    Write-Host "ℹ️  cypher-shell not available in PATH" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📊 Expected Performance Improvements:" -ForegroundColor Cyan
Write-Host "   - Depth 1 queries: 100-500ms → 10-50ms" -ForegroundColor White
Write-Host "   - Depth 2 queries: 2-10s → 100-500ms" -ForegroundColor White
Write-Host "   - Node lookup: 50-200ms → 5-20ms" -ForegroundColor White
Write-Host "   - Relationship traversal: 200-1000ms → 20-100ms" -ForegroundColor White

Write-Host ""
Write-Host "💡 After applying indexes, test performance with:" -ForegroundColor Yellow
Write-Host "   - Frontend: http://localhost:3000/lexical/graph" -ForegroundColor White
Write-Host "   - Set Depth to 2 and search for 'nihon'" -ForegroundColor White
Write-Host "   - Should load much faster now!" -ForegroundColor Green

Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Cyan
Write-Host "1. Apply indexes using Neo4j Browser or cypher-shell" -ForegroundColor White
Write-Host "2. Restart the backend server to ensure clean connections" -ForegroundColor White
Write-Host "3. Test the frontend with Depth 2 queries" -ForegroundColor White
Write-Host "4. Monitor performance improvements" -ForegroundColor White
