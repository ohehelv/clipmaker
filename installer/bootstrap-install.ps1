#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$RepoRef = "main",

    [string]$AppName = "Karaoke Maker",

    [string]$InstallRoot = "$env:LOCALAPPDATA\\KaraokeMaker"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Step([string]$Message) {
    Write-Host "[bootstrap] $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[bootstrap] $Message" -ForegroundColor Green
}

function Fail([string]$Message) {
    Write-Host "[bootstrap] $Message" -ForegroundColor Red
    throw $Message
}

function Confirm-RepoUrl([string]$Url) {
    if (-not ($Url -match '^https://github\.com/[^/]+/[^/]+(\.git)?$')) {
        Fail "RepoUrl должен быть HTTPS URL GitHub вида https://github.com/owner/repo(.git)"
    }
}

function Ensure-Tool([string]$ToolName, [string]$InstallUrl) {
    $cmd = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        Write-Ok "$ToolName найден: $($cmd.Source)"
        return
    }

    $answer = Read-Host "$ToolName не найден. Открыть официальный сайт для установки? [Y/N]"
    if ($answer -match '^(y|yes|д|да)$') {
        Start-Process $InstallUrl | Out-Null
    }
    Fail "$ToolName обязателен для работы установщика"
}

function Ensure-DockerCompose() {
    $output = & docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "docker compose доступен"
        return
    }
    Fail "Команда 'docker compose' недоступна. Установите/обновите Docker Desktop."
}

function Ensure-DockerRunning() {
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Docker daemon запущен"
        return
    }
    Fail "Docker daemon не запущен. Откройте Docker Desktop и дождитесь статуса Running."
}

function Get-ComposeFile([string]$ProjectDir) {
    $candidates = @(
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml"
    )

    foreach ($name in $candidates) {
        $candidate = Join-Path $ProjectDir $name
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function Sync-Repository([string]$ProjectDir, [string]$Url, [string]$Ref) {
    if (-not (Test-Path $ProjectDir)) {
        Write-Step "Клонирование проекта..."
        & git clone --filter=blob:none --branch $Ref --single-branch $Url $ProjectDir
        if ($LASTEXITCODE -ne 0) {
            Fail "Не удалось клонировать репозиторий"
        }
        return
    }

    Write-Step "Проект уже существует, обновляю до $Ref"
    $isRepo = Test-Path (Join-Path $ProjectDir ".git")
    if (-not $isRepo) {
        Fail "Папка проекта существует, но не является git-репозиторием: $ProjectDir"
    }

    $dirty = & git -C $ProjectDir status --porcelain
    if ($dirty) {
        Fail "В папке проекта есть локальные изменения. Очистите их вручную перед обновлением."
    }

    & git -C $ProjectDir fetch --depth 1 origin $Ref
    if ($LASTEXITCODE -ne 0) {
        Fail "Не удалось получить изменения из origin/$Ref"
    }

    & git -C $ProjectDir checkout --force FETCH_HEAD
    if ($LASTEXITCODE -ne 0) {
        Fail "Не удалось переключиться на актуальную ревизию"
    }
}

function Save-State([string]$StatePath, [string]$ProjectDir, [string]$Url, [string]$Ref) {
    $state = [ordered]@{
        appName = $AppName
        projectDir = $ProjectDir
        repoUrl = $Url
        repoRef = $Ref
        updatedAt = (Get-Date).ToString("o")
    }
    $json = $state | ConvertTo-Json
    Set-Content -Path $StatePath -Value $json -Encoding UTF8
}

function Start-Stack([string]$ProjectDir) {
    $composeFile = Get-ComposeFile -ProjectDir $ProjectDir
    if ($null -eq $composeFile) {
        Fail "Не найден compose-файл в проекте (docker-compose.yml/compose.yaml)"
    }

    Write-Step "Сборка и запуск контейнеров через docker compose"
    & docker compose -f $composeFile up -d --build
    if ($LASTEXITCODE -ne 0) {
        Fail "docker compose up завершился с ошибкой"
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSec = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

try {
    Confirm-RepoUrl -Url $RepoUrl

    Write-Step "Проверка зависимостей"
    Ensure-Tool -ToolName "git" -InstallUrl "https://git-scm.com/download/win"
    Ensure-Tool -ToolName "docker" -InstallUrl "https://www.docker.com/products/docker-desktop/"
    Ensure-DockerCompose
    Ensure-DockerRunning

    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
    $projectDir = Join-Path $InstallRoot "project"
    $statePath = Join-Path $InstallRoot "launcher-state.json"

    Sync-Repository -ProjectDir $projectDir -Url $RepoUrl -Ref $RepoRef
    Save-State -StatePath $statePath -ProjectDir $projectDir -Url $RepoUrl -Ref $RepoRef
    Start-Stack -ProjectDir $projectDir

    if (Wait-Http -Url "http://127.0.0.1:8000" -TimeoutSec 120) {
        Write-Ok "Сервис доступен на http://127.0.0.1:8000"
    } else {
        Write-Host "[bootstrap] Сервис не ответил за 120 секунд. Проверьте 'docker compose logs'." -ForegroundColor Yellow
    }

    Start-Process "http://127.0.0.1:8000" | Out-Null
    Write-Ok "Установка завершена"
}
catch {
    Write-Host "[bootstrap] Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}