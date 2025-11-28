# Requires PowerShell 5+
param(
    [string]$BaseUrl = "http://localhost:8000/api/v1",
    [int]$Limit = 200,
    [int]$Offset = 0,
    [int]$Version = 1,
    [string]$Provider = "openai"
)

Write-Host "[generate_lessons] BaseUrl=$BaseUrl Limit=$Limit Version=$Version"

function Get-CanDoPage {
    param(
        [int]$Limit,
        [int]$Offset
    )
    $url = "$BaseUrl/cando/list?limit=$Limit&offset=$Offset"
    try {
        return Invoke-RestMethod -Method GET -Uri $url -TimeoutSec 60
    } catch {
        Write-Warning "Failed to fetch CanDo list: $($_.Exception.Message)"
        return $null
    }
}

function Compile-CanDoLesson {
    param(
        [string]$CanDoId,
        [int]$Version,
        [string]$Provider
    )
    $url = "$BaseUrl/cando/lessons/compile?can_do_id=$([uri]::EscapeDataString($CanDoId))&version=$Version&provider=$Provider"
    try {
        $resp = Invoke-RestMethod -Method POST -Uri $url -TimeoutSec 120
        return $resp
    } catch {
        Write-Warning "Compile failed for $CanDoId: $($_.Exception.Message)"
        return $null
    }
}

$processed = 0
while ($true) {
    $page = Get-CanDoPage -Limit $Limit -Offset $Offset
    if (-not $page -or -not $page.items -or $page.items.Count -eq 0) {
        break
    }
    foreach ($item in $page.items) {
        $id = [string]$item.uid
        if (-not $id) { continue }
        Write-Host "Compiling can_do_id=$id version=$Version"
        $result = Compile-CanDoLesson -CanDoId $id -Version $Version -Provider $Provider
        if ($result) { $processed++ }
    }
    $Offset += $Limit
}

Write-Host "[generate_lessons] Done. Processed=$processed"




