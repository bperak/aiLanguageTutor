# Apply AI Content Schema to Neo4j
# Adds AI-generated content properties to Word nodes

param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Apply AI Content Schema Script" -ForegroundColor Green
    Write-Host "==============================" -ForegroundColor Green
    Write-Host ""
    Write-Host "This script applies the AI content schema to your Neo4j database."
    Write-Host "It adds properties and indexes for storing AI-generated word content."
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\scripts\apply_ai_content_schema.ps1"
    Write-Host ""
    Write-Host "Prerequisites:" -ForegroundColor Yellow
    Write-Host "  - Neo4j database running"
    Write-Host "  - Docker Compose services started"
    Write-Host "  - Environment variables configured"
    Write-Host ""
    exit 0
}

# Change to the project root directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "Applying AI Content Schema to Neo4j" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host "Project root: $projectRoot" -ForegroundColor Gray
Write-Host ""

# Check if Docker is running
try {
    docker ps | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
} catch {
    Write-Host "❌ Docker is not running. Please start Docker first." -ForegroundColor Red
    exit 1
}

# Check if Neo4j container is running
$neo4jContainer = docker ps --filter "name=neo4j" --format "{{.Names}}"
if (-not $neo4jContainer) {
    Write-Host "❌ Neo4j container is not running." -ForegroundColor Red
    Write-Host "Please start the services with: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Neo4j container is running: $neo4jContainer" -ForegroundColor Green

# Apply the schema
$schemaFile = "backend/migrations/ai_content_schema.cypher"
if (-not (Test-Path $schemaFile)) {
    Write-Host "❌ Schema file not found: $schemaFile" -ForegroundColor Red
    exit 1
}

Write-Host "Applying schema from: $schemaFile" -ForegroundColor Blue

try {
    # Copy the schema file to the Neo4j container and execute it
    docker cp $schemaFile "${neo4jContainer}:/tmp/ai_content_schema.cypher"
    
    # Execute the schema
    docker exec $neo4jContainer cypher-shell -u neo4j -p testpassword123 -f /tmp/ai_content_schema.cypher
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ AI Content Schema applied successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "The following have been added:" -ForegroundColor Cyan
        Write-Host "  - AI content properties to Word nodes" -ForegroundColor Gray
        Write-Host "  - Indexes for AI content queries" -ForegroundColor Gray
        Write-Host "  - Constraints for content versioning" -ForegroundColor Gray
        Write-Host ""
        Write-Host "You can now:" -ForegroundColor Yellow
        Write-Host "  - Generate AI content using the API endpoints" -ForegroundColor Gray
        Write-Host "  - Run background generation scripts" -ForegroundColor Gray
        Write-Host "  - Use the enhanced Info panel in the frontend" -ForegroundColor Gray
    } else {
        Write-Host "❌ Failed to apply schema. Check Neo4j logs." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error applying schema: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Schema application completed!" -ForegroundColor Green
