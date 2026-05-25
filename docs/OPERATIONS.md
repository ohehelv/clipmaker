# Эксплуатация

## Запуск

```powershell
.\start.ps1
```

Публичный HTTPS режим:

```powershell
.\start.ps1 -Edge
```

## Остановка

```powershell
docker compose down
```

Для edge-режима:

```powershell
docker compose -f docker-compose.yml -f docker-compose.edge.yml down
```

## Обновление

```powershell
git pull --ff-only
docker compose build
docker compose up -d
```

Для edge-режима:

```powershell
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.edge.yml build
docker compose -f docker-compose.yml -f docker-compose.edge.yml up -d
```

## Логи

```powershell
docker compose logs -f clipmaker
```

Логи Caddy (edge):

```powershell
docker compose -f docker-compose.yml -f docker-compose.edge.yml logs -f caddy
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
