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
  [switch]$NoBrowser,
  [switch]$Edge
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

if ($Edge) {
  & docker compose -f docker-compose.yml -f docker-compose.edge.yml up -d
}
else {
  & docker compose up -d
}
if ($LASTEXITCODE -ne 0) {
  Write-Host "Не удалось поднять контейнеры" -ForegroundColor Red
  exit 1
}

if (-not $NoBrowser) {
  $targetUrl = "http://127.0.0.1:$Port"
  if ($Edge) {
    $envFile = Join-Path $PSScriptRoot ".env"
    if (Test-Path $envFile) {
      $domainLine = Get-Content $envFile | Where-Object { $_ -match '^APP_DOMAIN=' } | Select-Object -First 1
      if ($domainLine) {
        $domain = ($domainLine -replace '^APP_DOMAIN=', '').Trim()
        if ($domain) {
          $targetUrl = "https://$domain"
        }
      }
    }
  }

    Start-Job -ScriptBlock {
    param($url)
        Start-Sleep -Seconds 4
    Start-Process $url
  } -ArgumentList $targetUrl | Out-Null
}

if ($Edge) {
  Write-Host "ClipMaker запущен в edge-режиме (Caddy + HTTPS)." -ForegroundColor Green
}
else {
  Write-Host "ClipMaker запущен. Откройте http://127.0.0.1:$Port" -ForegroundColor Green
}
