# Эксплуатация

## Запуск

```powershell
.\start.ps1
```

## Остановка

```powershell
docker compose down
```

## Обновление

```powershell
git pull --ff-only
docker compose build
docker compose up -d
```

## Логи

```powershell
docker compose logs -f clipmaker
```

## Бэкап данных

Сохраняйте папку `data/`:

- `data/uploads`
- `data/jobs`
- `data/outputs`

## Healthcheck вручную

- API: `http://127.0.0.1:8000/api/models`
- UI: `http://127.0.0.1:8000`

Если включен `API_KEY`, запросы к API должны содержать `X-API-Key`.
