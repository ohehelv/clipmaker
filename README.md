# ClipMaker

Локальная система генерации музыкальных клипов: MP3 + текст песни + промт → видео-клип.

## Возможности

- Загрузка MP3, текста песни и общего промта.
- 4 режима построения клипа:
  1. **whisper** — выравнивание лирики по времени через Whisper, сцена на строку/куплет.
  2. **llm** — LLM-режиссёр (OpenRouter) формирует сценарий из промта и лирики.
  3. **uniform** — равное разбиение по N сцен.
  4. **single** — одна длинная сцена на весь трек (img2video).
- Подключаемые генераторы видео через ComfyUI:
  - AnimateDiff, Stable Video Diffusion, CogVideoX, HunyuanVideo, Wan 2.1, Mochi-1, LTX-Video.
  - Заглушка `stub` для end-to-end теста без GPU.
- Финальная склейка ffmpeg: сцены + аудио (+ опционально субтитры).
- Web UI (FastAPI + статический HTML/JS).

## Стек

- Python 3.11+, FastAPI, Uvicorn.
- Docker Desktop + Docker Compose (основной способ запуска).
- `faster-whisper` для транскрипции/таймкодов.
- `httpx` для OpenRouter и ComfyUI HTTP API.
- `ffmpeg` внутри контейнера.
- ComfyUI запускается отдельно (обычно на хосте, URL через `COMFYUI_URL`).

## Быстрый старт (Windows + Docker)

```powershell
cd e:\clipmaker
.\setup.ps1
.\start.ps1
```

Открыть http://127.0.0.1:8000

## Публичный HTTPS режим (Caddy)

1. Заполните в `.env`: `APP_DOMAIN`, `ACME_EMAIL`, `CADDY_BASIC_AUTH_HASH`.
2. Обновите `CORS_ORIGINS` под ваш https-домен.
3. Запустите:

```powershell
.\start.ps1 -Edge
```

После этого внешний вход идёт через Caddy на `https://<ваш-домен>`,
а backend остаётся привязан к localhost (`127.0.0.1:8000`).

## Основные переменные окружения

- `COMFYUI_URL` — адрес ComfyUI (по умолчанию для Docker: `http://host.docker.internal:8188`).
- `OPENROUTER_API_KEY` — ключ OpenRouter для LLM режима.
- `API_KEY` — если задан, API требует `X-API-Key` или `Authorization: Bearer ...`.
- `CORS_ORIGINS` — список origin через запятую.

Шаблон: [.env.example](.env.example)

## Документация

- [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)
- [docs/SECURITY.md](docs/SECURITY.md)
- [docs/RELEASE.md](docs/RELEASE.md)
- [docs/DEPLOY_PUBLIC.md](docs/DEPLOY_PUBLIC.md)

## Структура

```
backend/
  main.py              FastAPI app
  config.py            настройки (.env)
  schemas.py           pydantic-модели запросов/ответов
  api/jobs.py          REST API задач
  api/models.py        список доступных видеомоделей
  core/alignment.py    выравнивание лирики (Whisper)
  core/scenes.py       4 режима планирования сцен
  core/llm.py          OpenRouter клиент
  core/prompts.py      шаблоны промтов
  core/compose.py      ffmpeg-склейка
  generators/          реестр и реализации видеогенераторов
    base.py
    registry.py
    comfyui_client.py
    stub.py
    animatediff.py, svd.py, cogvideox.py, hunyuan.py, wan.py, mochi.py, ltx.py
    workflows/*.json   ComfyUI workflow-шаблоны (заглушки)
  jobs/queue.py        in-process очередь задач
  jobs/runner.py       пайплайн
frontend/
  index.html, app.js, style.css
data/
  uploads/  jobs/  outputs/
tempscripts/           разовые скрипты
```

## Статус

Скелет. Видеогенераторы — заглушки (кроме `stub`, который рендерит цветные плейсхолдеры). Реальные ComfyUI workflows подключаются по мере необходимости — кладутся в `backend/generators/workflows/` и используются клиентом.

## Windows Installer (Inno Setup)

Для локальной установки (для себя/небольшой группы) добавлен инсталлятор в папке `installer/`.

Что делает инсталлятор:

- проверяет наличие `git`, `docker`, `docker compose`;
- клонирует проект из GitHub в `%LOCALAPPDATA%\\KaraokeMaker\\project`;
- запускает `docker compose up -d --build`;
- создаёт ярлык `Запустить Karaoke Maker`.

### Сборка `.exe`

1. Установить Inno Setup 6.
2. Выполнить в PowerShell:

```powershell
cd e:\clipmaker\installer
.\build-installer.ps1 -RepoUrl https://github.com/ohehelv/clipmaker.git -RepoRef main
```

Готовый файл будет в `installer\\output\\KaraokeMakerSetup.exe`.

### Важно по безопасности

- Инсталлятор работает в контексте текущего пользователя (`PrivilegesRequired=lowest`) и не требует админ-прав.
- Используйте только ваш HTTPS GitHub URL.
- Для раздачи вне доверенного круга лучше подписать `.exe` code-sign сертификатом.
