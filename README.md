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
- `faster-whisper` для транскрипции/таймкодов.
- `httpx` для OpenRouter и ComfyUI HTTP API.
- `ffmpeg` (внешний бинарник в PATH).
- ComfyUI запущен отдельно (по умолчанию `http://127.0.0.1:8188`).

## Установка

```powershell
cd e:\clipmaker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Прописать OPENROUTER_API_KEY и COMFYUI_URL
```

ffmpeg должен быть в PATH. ComfyUI ставится отдельно (см. https://github.com/comfyanonymous/ComfyUI).

## Запуск

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Открыть http://127.0.0.1:8000

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

## Дальнейшие шаги

1. Запустить ComfyUI, установить нужные модели/ноды.
2. Заменить заглушки `workflows/*.json` на реальные экспорты из ComfyUI (Save (API Format)).
3. Откорректировать параметры узлов в соответствующих `generators/<model>.py`.

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
.\build-installer.ps1 -RepoUrl https://github.com/<owner>/<repo>.git -RepoRef main
```

Готовый файл будет в `installer\\output\\KaraokeMakerSetup.exe`.

### Важно по безопасности

- Инсталлятор работает в контексте текущего пользователя (`PrivilegesRequired=lowest`) и не требует админ-прав.
- Используйте только ваш HTTPS GitHub URL.
- Для раздачи вне доверенного круга лучше подписать `.exe` code-sign сертификатом.
