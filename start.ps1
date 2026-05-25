#requires -Version 5.1
<#
.SYNOPSIS
  Запуск ClipMaker (FastAPI). ComfyUI поднимется автоматически из бэкенда.

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

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "venv не найден. Сначала: .\setup.ps1" -ForegroundColor Red
    exit 1
}

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($p)
        Start-Sleep -Seconds 4
        Start-Process "http://127.0.0.1:$p"
    } -ArgumentList $Port | Out-Null
}

& $venvPy -m uvicorn backend.main:app --host 127.0.0.1 --port $Port
