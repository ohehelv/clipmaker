# Установка на Windows

## Требования

- Windows 10/11 x64.
- Docker Desktop (WSL2 backend включен).
- NVIDIA драйвер и рабочий ComfyUI на хосте (если используете GPU-генерацию).

## Рекомендуемый путь

1. Клонируйте проект.
2. Скопируйте `.env.example` в `.env`.
3. Запустите:

```powershell
.\setup.ps1
.\start.ps1
```

4. Откройте `http://127.0.0.1:8000`.

## Проверка ComfyUI

- По умолчанию в Docker используется `COMFYUI_URL=http://host.docker.internal:8188`.
- Проверьте, что ComfyUI отвечает с хоста:

```powershell
curl http://127.0.0.1:8188/system_stats
```

## Inno Setup инсталлятор

1. Установите Inno Setup 6.
2. Соберите инсталлятор:

```powershell
cd installer
.\build-installer.ps1 -RepoUrl https://github.com/ohehelv/clipmaker.git -RepoRef main
```

3. Готовый файл: `installer/output/KaraokeMakerSetup.exe`.
