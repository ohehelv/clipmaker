# Публичный деплой (Caddy + HTTPS)

## Что даёт этот режим

- Внешний трафик только через `https://<домен>`.
- TLS сертификаты от Let's Encrypt через Caddy.
- Basic Auth на ` /api/* ` на уровне reverse proxy.
- Backend API остаётся на `127.0.0.1:8000` и не открыт наружу напрямую.

## Подготовка сервера

1. Откройте входящие порты `80` и `443`.
2. Настройте DNS A/AAAA запись домена на IP сервера.
3. Установите Docker Desktop/Engine и Docker Compose.

## Настройка `.env`

Укажите:

- `APP_DOMAIN=your-domain.example`
- `ACME_EMAIL=you@example.com`
- `CADDY_BASIC_AUTH_USER=admin`
- `CADDY_BASIC_AUTH_HASH=<bcrypt-hash>`
- `API_KEY=<случайная-строка>`
- `CORS_ORIGINS=https://your-domain.example`

Генерация bcrypt-хэша:

```powershell
docker run --rm caddy:2.9 caddy hash-password --plaintext "CHANGE_ME"
```

## Запуск

```powershell
.\start.ps1 -Edge
```

## Проверка

1. Откройте `https://your-domain.example`.
2. Проверьте, что `http://<ip>:8000` снаружи недоступен.
3. Проверьте API с auth-заголовком:

```powershell
curl -H "X-API-Key: <API_KEY>" https://your-domain.example/api/models
```

## Обновление

```powershell
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.edge.yml build
docker compose -f docker-compose.yml -f docker-compose.edge.yml up -d
```

## Важные замечания

- В стандартном образе Caddy нет встроенного rate-limit модуля.
- Для жёсткого rate-limit добавьте внешний WAF/CDN (Cloudflare) или специализированный API gateway.
