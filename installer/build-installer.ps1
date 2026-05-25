#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$RepoRef = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not ($RepoUrl -match '^https://github\.com/[^/]+/[^/]+(\.git)?$')) {
    throw "RepoUrl должен быть HTTPS URL GitHub вида https://github.com/owner/repo(.git)"
}

$iss = Join-Path $PSScriptRoot "KaraokeMakerInstaller.iss"
if (-not (Test-Path $iss)) {
    throw "Не найден Inno скрипт: $iss"
}

$iscc = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
if ($null -eq $iscc) {
    $defaultPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $defaultPath) {
        $isccPath = $defaultPath
    } else {
        throw "ISCC.exe не найден. Установите Inno Setup 6: https://jrsoftware.org/isdl.php"
    }
} else {
    $isccPath = $iscc.Source
}

& $isccPath "/DRepoUrl=$RepoUrl" "/DRepoRef=$RepoRef" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Сборка инсталлятора завершилась с ошибкой"
}

Write-Host "Готово. Инсталлятор в папке installer\\output" -ForegroundColor Green