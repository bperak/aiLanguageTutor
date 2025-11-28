# AI Content Generation Script for Windows PowerShell
# Generates AI-enhanced content for words in the lexical graph

param(
    [string]$Word = "",
    [string]$Difficulty = "1-6",
    [int]$Limit = 50,
    [switch]$Force,
    [double]$Delay = 1.0,
    [switch]$DryRun,
    [switch]$Help
)

if ($Help) {
    Write-Host "AI Content Generation Script" -ForegroundColor Green
    Write-Host "=============================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\scripts\generate_ai_content.ps1 [options]"
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Word <string>        Generate content for a specific word (e.g., '水')"
    Write-Host "  -Difficulty <string>  Difficulty range (e.g., '1-3' or '4-6') [default: 1-6]"
    Write-Host "  -Limit <int>          Maximum number of words to process [default: 50]"
    Write-Host "  -Force                Force regenerate existing content"
    Write-Host "  -Delay <double>       Delay between requests in seconds [default: 1.0]"
    Write-Host "  -DryRun               Show what would be processed without generating"
    Write-Host "  -Help                 Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\scripts\generate_ai_content.ps1 -Word '水' -Force"
    Write-Host "  .\scripts\generate_ai_content.ps1 -Difficulty '1-3' -Limit 100"
    Write-Host "  .\scripts\generate_ai_content.ps1 -DryRun -Limit 20"
    Write-Host ""
    exit 0
}

# Change to the project root directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "AI Content Generation Script" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host "Project root: $projectRoot" -ForegroundColor Gray
Write-Host ""

# Check if Python virtual environment exists
$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "❌ Python virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv && .venv\Scripts\activate && pip install -r backend/requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "Activating Python virtual environment..." -ForegroundColor Blue
& "$venvPath\Scripts\Activate.ps1"

# Check if required packages are installed
Write-Host "Checking dependencies..." -ForegroundColor Blue
try {
    python -c "import fastapi, neo4j" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Missing dependencies"
    }
} catch {
    Write-Host "❌ Missing required dependencies. Installing..." -ForegroundColor Yellow
    pip install -r backend/requirements.txt
}

# Build command arguments
$args = @()

if ($Word) {
    $args += "--word", $Word
}

if ($Difficulty -ne "1-6") {
    $args += "--difficulty", $Difficulty
}

if ($Limit -ne 50) {
    $args += "--limit", $Limit
}

if ($Force) {
    $args += "--force"
}

if ($Delay -ne 1.0) {
    $args += "--delay", $Delay
}

if ($DryRun) {
    $args += "--dry-run"
}

# Display configuration
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Word: $(if ($Word -eq '') { 'All words in range' } else { $Word })" -ForegroundColor Gray
Write-Host "  Difficulty: $Difficulty" -ForegroundColor Gray
Write-Host "  Limit: $Limit" -ForegroundColor Gray
Write-Host "  Force: $Force" -ForegroundColor Gray
Write-Host "  Delay: $Delay seconds" -ForegroundColor Gray
Write-Host "  Dry Run: $DryRun" -ForegroundColor Gray
Write-Host ""

# Run the Python script
Write-Host "Starting AI content generation..." -ForegroundColor Green
Write-Host "Command: python scripts/generate_ai_content_background.py $($args -join ' ')" -ForegroundColor Gray
Write-Host ""

try {
    python scripts/generate_ai_content_background.py @args
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "✅ AI content generation completed successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ AI content generation failed with exit code: $exitCode" -ForegroundColor Red
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error running AI content generation: $_" -ForegroundColor Red
    $exitCode = 1
}

# Deactivate virtual environment
deactivate

Write-Host ""
Write-Host "Script completed. Check ai_content_generation.log for detailed logs." -ForegroundColor Blue

exit $exitCode
