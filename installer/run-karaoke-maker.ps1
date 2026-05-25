#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host "[launcher] $Message" -ForegroundColor Red
    throw $Message
}

function Get-StatePath() {
    $base = Split-Path -Parent $PSCommandPath
    return Join-Path $base "launcher-state.json"
}

function Get-ComposeFile([string]$ProjectDir) {
    foreach ($name in @("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")) {
        $candidate = Join-Path $ProjectDir $name
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

try {
    $statePath = Get-StatePath
    if (-not (Test-Path $statePath)) {
        Fail "Не найден launcher-state.json. Запустите установку заново."
    }

    $state = Get-Content -Path $statePath -Raw | ConvertFrom-Json
    $projectDir = [string]$state.projectDir
    if (-not (Test-Path $projectDir)) {
        Fail "Папка проекта не найдена: $projectDir"
    }

    $composeFile = Get-ComposeFile -ProjectDir $projectDir
    if ($null -eq $composeFile) {
        Fail "Compose-файл не найден в $projectDir"
    }

    & docker compose -f $composeFile up -d
    if ($LASTEXITCODE -ne 0) {
        Fail "Не удалось запустить контейнеры"
    }

    if (-not $NoBrowser) {
        Start-Process "http://127.0.0.1:8000" | Out-Null
    }

    Write-Host "[launcher] Karaoke Maker запущен" -ForegroundColor Green
}
catch {
    Write-Host "[launcher] Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}