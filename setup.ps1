#requires -Version 5.1
<#
.SYNOPSIS
  Авто-установка ClipMaker: venv, зависимости, ComfyUI, custom-ноды, веса Wan 2.2.

.PARAMETER OpenRouterKey
  Ключ OpenRouter. Запишется в .env. Если пусто — будет запрос интерактивно.

.PARAMETER HfToken
  Опционально: токен HuggingFace для приватных репо.

.PARAMETER SkipModels
  Не качать веса моделей (≈20 ГБ). Полезно для отладки установки.

.PARAMETER ModelsDir
  Использовать существующую папку models (например от другого ComfyUI).
  По умолчанию: vendor\ComfyUI\models.

.EXAMPLE
  .\setup.ps1 -OpenRouterKey sk-or-...
#>
param(
    [string]$OpenRouterKey = "",
    [string]$HfToken = "",
    [switch]$SkipModels,
    [string]$ModelsDir = ""
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Info($msg)   { Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Warn($msg)   { Write-Host "[setup] $msg" -ForegroundColor Yellow }
function Ok($msg)     { Write-Host "[setup] $msg" -ForegroundColor Green }
function Fail($msg)   { Write-Host "[setup] $msg" -ForegroundColor Red; exit 1 }

# 1. Python
Info "Проверка Python 3.11+"
$py = $null
foreach ($cmd in @("python", "py -3.11", "py -3.12", "python3")) {
    try {
        $v = & cmd /c "$cmd --version 2>&1"
        if ($LASTEXITCODE -eq 0 -and $v -match "Python 3\.(11|12)") {
            $py = $cmd
            Ok "Найден: $v ($cmd)"
            break
        }
    } catch {}
}
if (-not $py) { Fail "Нужен Python 3.11 или 3.12. Установи с https://www.python.org/downloads/" }

# 2. venv
if (-not (Test-Path ".venv")) {
    Info "Создание venv"
    & cmd /c "$py -m venv .venv"
}
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Fail ".venv не создан" }

# 3. pip upgrade + базовые
Info "Обновление pip"
& $venvPy -m pip install --upgrade pip wheel setuptools | Out-Null

Info "Установка зависимостей ClipMaker"
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "pip install requirements.txt упал" }

# 4. PyTorch (CUDA 12.4) — для RTX 5090 (Blackwell)
Info "Установка PyTorch + CUDA 12.4 (может занять несколько минут)"
& $venvPy -m pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) {
    Warn "Stable cu124 не подошёл, пробуем nightly cu124"
    & $venvPy -m pip install --pre --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu124
    if ($LASTEXITCODE -ne 0) { Fail "PyTorch не установился" }
}

# 5. ComfyUI
$comfyDir = Join-Path $PSScriptRoot "vendor\ComfyUI"
if (-not (Test-Path $comfyDir)) {
    Info "Клонирование ComfyUI"
    New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "vendor") | Out-Null
    git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $comfyDir
    if ($LASTEXITCODE -ne 0) { Fail "git clone ComfyUI" }
} else {
    Info "ComfyUI уже клонирован — git pull"
    Push-Location $comfyDir
    git pull --ff-only 2>&1 | Out-Null
    Pop-Location
}

Info "Установка зависимостей ComfyUI"
& $venvPy -m pip install -r (Join-Path $comfyDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "ComfyUI requirements" }

# 6. Custom nodes
$nodes = @(
    @{ name = "ComfyUI-Manager";              url = "https://github.com/ltdrdata/ComfyUI-Manager.git" },
    @{ name = "ComfyUI-VideoHelperSuite";     url = "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" },
    @{ name = "ComfyUI-KJNodes";              url = "https://github.com/kijai/ComfyUI-KJNodes.git" },
    @{ name = "ComfyUI-Frame-Interpolation";  url = "https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git" }
)
$nodesDir = Join-Path $comfyDir "custom_nodes"
New-Item -ItemType Directory -Force -Path $nodesDir | Out-Null
foreach ($n in $nodes) {
    $dst = Join-Path $nodesDir $n.name
    if (-not (Test-Path $dst)) {
        Info "Клонирование $($n.name)"
        git clone --depth 1 $n.url $dst
    } else {
        Info "$($n.name) уже установлен"
    }
    $req = Join-Path $dst "requirements.txt"
    if (Test-Path $req) {
        Info "  → requirements"
        & $venvPy -m pip install -r $req | Out-Null
    }
}

# 7. ModelsDir
if ($ModelsDir -ne "") {
    if (-not (Test-Path $ModelsDir)) { Fail "ModelsDir не существует: $ModelsDir" }
    $linkTarget = Join-Path $comfyDir "models"
    if (Test-Path $linkTarget) { Remove-Item -Recurse -Force $linkTarget }
    Info "Симлинк models → $ModelsDir"
    New-Item -ItemType Junction -Path $linkTarget -Target $ModelsDir | Out-Null
}

# 8. Скачивание весов Wan 2.2 через huggingface_hub
if (-not $SkipModels) {
    Info "Скачивание весов Wan 2.2 (≈18 ГБ, может быть долго)"
    if ($HfToken -ne "") { $env:HF_TOKEN = $HfToken }
    $dl = @"
import os
from huggingface_hub import hf_hub_download

base = r'$comfyDir' + '/models'
os.makedirs(base + '/diffusion_models', exist_ok=True)
os.makedirs(base + '/text_encoders', exist_ok=True)
os.makedirs(base + '/vae', exist_ok=True)

# Wan 2.2 T2V 14B fp8_scaled (high+low noise — ComfyOrg комплект)
downloads = [
    ('Comfy-Org/Wan_2.2_ComfyUI_Repackaged', 'split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors', 'diffusion_models'),
    ('Comfy-Org/Wan_2.2_ComfyUI_Repackaged', 'split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors',  'diffusion_models'),
    ('Comfy-Org/Wan_2.2_ComfyUI_Repackaged', 'split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors',              'text_encoders'),
    ('Comfy-Org/Wan_2.2_ComfyUI_Repackaged', 'split_files/vae/wan_2.1_vae.safetensors',                                       'vae'),
]
for repo, path, sub in downloads:
    print(f'>>> {path}')
    out = hf_hub_download(repo_id=repo, filename=path, local_dir=base + '/' + sub, local_dir_use_symlinks=False)
    print(f'    -> {out}')
print('OK')
"@
    $tmp = Join-Path $env:TEMP "clipmaker_dl.py"
    Set-Content -Path $tmp -Value $dl -Encoding UTF8
    & $venvPy -m pip install --upgrade huggingface_hub | Out-Null
    & $venvPy $tmp
    if ($LASTEXITCODE -ne 0) { Warn "Скачивание весов не завершилось — можно перезапустить setup.ps1 без -SkipModels" }
    Remove-Item $tmp -ErrorAction SilentlyContinue
} else {
    Warn "Пропуск скачивания весов (-SkipModels)"
}

# 9. .env
$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Info "Создание .env"
    Copy-Item -Path ".env.example" -Destination ".env"
}
if ($OpenRouterKey -eq "") {
    $OpenRouterKey = Read-Host -Prompt "OpenRouter API key (Enter — пропустить)"
}
if ($OpenRouterKey -ne "") {
    $content = Get-Content $envFile -Raw
    if ($content -match "^OPENROUTER_API_KEY=") {
        $content = $content -replace "OPENROUTER_API_KEY=.*", "OPENROUTER_API_KEY=$OpenRouterKey"
    } else {
        $content += "`nOPENROUTER_API_KEY=$OpenRouterKey"
    }
    Set-Content -Path $envFile -Value $content -Encoding UTF8 -NoNewline
    Ok "OPENROUTER_API_KEY записан в .env"
}

Ok "Установка завершена. Запусти: .\start.ps1"
