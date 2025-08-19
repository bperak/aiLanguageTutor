Param(
    [string]$ApiBaseUrl = $env:API_BASE_URL
)

if (-not $ApiBaseUrl) { $ApiBaseUrl = "http://localhost:8000" }
Write-Host "API_BASE_URL: $ApiBaseUrl"

if (-not (Test-Path ".venv")) { python -m venv .venv }

& .\.venv\Scripts\Activate.ps1

python -m pip install -U pip; pip install pytest requests

$env:API_BASE_URL = $ApiBaseUrl

# Wait for backend health (up to ~30s)
$maxTries = 15; $ok = $false
for ($i = 0; $i -lt $maxTries; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$ApiBaseUrl/health" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) { $ok = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ok) { Write-Warning "Backend health endpoint not responding; continuing to run tests..." }

pytest -q tests

exit $LASTEXITCODE


