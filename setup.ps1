#requires -Version 5.1
<#
.SYNOPSIS
  Подготовка ClipMaker к запуску через Docker Desktop.

.DESCRIPTION
  Скрипт проверяет Docker, создает .env из .env.example (если нужно)
  и выполняет сборку контейнера backend.

.PARAMETER OpenRouterKey
  Опционально записывает OPENROUTER_API_KEY в .env.

.PARAMETER NoBuild
  Пропустить сборку docker image.
#>
param(
    [string]$OpenRouterKey = "",
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Info($msg) { Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "[setup] $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "[setup] $msg" -ForegroundColor Red; exit 1 }

function Ensure-Cmd($name, $url) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        Ok "$name найден"
        return
    }
    Start-Process $url | Out-Null
    Fail "$name не найден. Установите и запустите снова."
}

Info "Проверка Docker Desktop"
Ensure-Cmd "docker" "https://www.docker.com/products/docker-desktop/"

& docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail "Команда docker compose недоступна" }

& docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker daemon не запущен. Откройте Docker Desktop" }

$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Info "Создание .env из .env.example"
    Copy-Item -Path ".env.example" -Destination ".env"
}

if ($OpenRouterKey -eq "") {
    $OpenRouterKey = Read-Host -Prompt "OpenRouter API key (Enter — пропустить)"
}
if ($OpenRouterKey -ne "") {
    $content = Get-Content $envFile -Raw
    if ($content -match "(?m)^OPENROUTER_API_KEY=.*$") {
        $content = [regex]::Replace($content, "(?m)^OPENROUTER_API_KEY=.*$", "OPENROUTER_API_KEY=$OpenRouterKey")
    } else {
        $content += "`r`nOPENROUTER_API_KEY=$OpenRouterKey"
    }
    Set-Content -Path $envFile -Value $content -Encoding UTF8 -NoNewline
    Ok "OPENROUTER_API_KEY записан в .env"
}

if (-not $NoBuild) {
    Info "Сборка Docker image"
    & docker compose build
    if ($LASTEXITCODE -ne 0) { Fail "docker compose build завершился с ошибкой" }
}

Ok "Готово. Запуск: .\start.ps1"
