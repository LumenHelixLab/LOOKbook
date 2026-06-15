# pipeline-research-story.ps1 — Portfolio E2E: NOTEtoolsLM vault export → lookBOOK import
# Usage:
#   pwsh D:\projects\scripts\pipeline-research-story.ps1
#   pwsh D:\projects\scripts\pipeline-research-story.ps1 -ChainVisual
#   pwsh D:\projects\scripts\pipeline-research-story.ps1 -ChainVisual -Push

param(
    [switch]$ChainVisual,
    [switch]$Push,
    [string]$CineforgeUrl = "http://127.0.0.1:8765",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$root = "D:\projects"
$lookbook = Join-Path $root "lookBOOK"
$notetools = Join-Path $root "NOTEtoolsLM-v2"
$fixture = Join-Path $root "scripts\fixtures\research-story-manifest.json"
$lastRunPath = Join-Path $root "scripts\.pipeline-research-story-last-run.json"
$workRoot = Join-Path $env:TEMP "pipeline-research-story"
$projectDir = Join-Path $workRoot "vault-demo"
$startedAt = (Get-Date).ToUniversalTime().ToString("o")

$report = [ordered]@{
    ok            = $false
    started_at    = $startedAt
    finished_at   = $null
    steps         = @()
    project_path  = $null
    files_written = 0
    chained_visual = $false
    error         = $null
}

function Add-Step([string]$Name, [bool]$Pass, [string]$Detail = "") {
    $report.steps += [ordered]@{ name = $Name; pass = $Pass; detail = $Detail }
    $icon = if ($Pass) { "PASS" } else { "FAIL" }
    $color = if ($Pass) { "Green" } else { "Red" }
    Write-Host "[$icon] $Name" -ForegroundColor $color
    if ($Detail) { Write-Host "      $Detail" -ForegroundColor DarkGray }
    if (-not $Pass) { throw "Step failed: $Name — $Detail" }
}

function Write-LastRun {
    $report.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $lastRunPath -Encoding utf8
}

try {
    Write-Host "`n=== Research→Story Pipeline E2E ===" -ForegroundColor Cyan
    Write-Host "NOTEtoolsLM vault manifest -> lookBOOK source import (M11)`n"

    Add-Step "fixture present" (Test-Path $fixture) $fixture
    Add-Step "lookBOOK vault_import module" (Test-Path (Join-Path $lookbook "lookbook\pipeline\vault_import.py")) $lookbook
    Add-Step "NOTEtoolsLM portfolio-export" (Test-Path (Join-Path $notetools "lib\portfolio-export.js")) $notetools

    if (Test-Path $workRoot) { Remove-Item -Recurse -Force $workRoot }
    New-Item -ItemType Directory -Path $workRoot -Force | Out-Null

    Push-Location $lookbook
    try {
        $importPy = @"
import json, sys
from pathlib import Path
from lookbook.pipeline.vault_import import import_vault_manifest, SOURCE_MANIFEST_SCHEMA

fixture = Path(r'$fixture')
manifest = json.loads(fixture.read_text(encoding='utf-8'))
assert manifest['format'] == SOURCE_MANIFEST_SCHEMA
project = Path(r'$projectDir')
result = import_vault_manifest(project, manifest)
print(json.dumps(result))
"@
        $importOut = python -c $importPy 2>&1
        if ($LASTEXITCODE -ne 0) { Add-Step "lookBOOK vault import" $false ($importOut -join "`n") }
        $importJson = $importOut | ConvertFrom-Json
        $report.project_path = $importJson.project
        $report.files_written = [int]$importJson.files_written
        Add-Step "lookBOOK vault import" $true "$($report.files_written) file(s) -> $projectDir"

        $recordPath = Join-Path $projectDir "analysis\vault_import.json"
        Add-Step "vault_import record" (Test-Path $recordPath) $recordPath
        $sourceMd = Join-Path $projectDir "source\ai-video-research.md"
        Add-Step "source markdown" (Test-Path $sourceMd) $sourceMd
    }
    finally { Pop-Location }

    if (-not $SkipTests) {
        Push-Location $notetools
        try {
            node --test tests/portfolio-export.test.js 2>&1 | Out-Host
            Add-Step "NOTEtoolsLM portfolio-export tests" ($LASTEXITCODE -eq 0)
        }
        finally { Pop-Location }

        Push-Location $lookbook
        try {
            pytest --basetemp=D:\tmp\pytest -q tests/test_vault_import.py 2>&1 | Out-Host
            Add-Step "lookBOOK vault_import pytest" ($LASTEXITCODE -eq 0)
        }
        finally { Pop-Location }
    }
    else {
        Add-Step "unit tests" $true "skipped (-SkipTests)"
    }

    if ($ChainVisual) {
        $visualArgs = @("-File", (Join-Path $root "scripts\pipeline-visual-story.ps1"), "-SkipTests")
        if ($Push) { $visualArgs += "-Push"; $visualArgs += "-CineforgeUrl"; $visualArgs += $CineforgeUrl }
        & pwsh @visualArgs
        Add-Step "chain visual-story E2E" ($LASTEXITCODE -eq 0)
        $report.chained_visual = $true
    }
    else {
        Add-Step "chain visual" $true "skipped (pass -ChainVisual to run M9 after import)"
    }

    $report.ok = $true
    Write-LastRun
    Write-Host "`nResearch→Story pipeline E2E: OK" -ForegroundColor Green
    exit 0
}
catch {
    $report.ok = $false
    $report.error = $_.Exception.Message
    Write-LastRun
    Write-Host "`nResearch→Story pipeline E2E: FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}