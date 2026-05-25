#requires -Version 5.1
<#
.SYNOPSIS
  Запуск ClipMaker через Docker Compose.

.PARAMETER Port
  Порт FastAPI. По умолчанию 8000.

.PARAMETER NoBrowser
  Не открывать браузер автоматически.
#>
param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "docker compose недоступен. Сначала: .\setup.ps1" -ForegroundColor Red
    exit 1
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker daemon не запущен" -ForegroundColor Red
  exit 1
}

& docker compose up -d
if ($LASTEXITCODE -ne 0) {
  Write-Host "Не удалось поднять контейнеры" -ForegroundColor Red
  exit 1
}

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($p)
        Start-Sleep -Seconds 4
        Start-Process "http://127.0.0.1:$p"
    } -ArgumentList $Port | Out-Null
}
Write-Host "ClipMaker запущен. Откройте http://127.0.0.1:$Port" -ForegroundColor Green
