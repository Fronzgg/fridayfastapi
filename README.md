# FRIDAY Cloud

Это отдельный Render-сервис для:

- `GET /api/state`
- `GET /api/cloud/state`
- `POST /api/admin/cloud`
- `POST /api/admin/cloud/news`
- `/admin` для ручной правки JSON

## Что пушить

Пушь только папку `onrender-cloud`.

## Что нужно в Render

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Root Directory: `onrender-cloud`

## Переменные окружения

- `FRIDAY_VERSION` - версия релиза
- `FRIDAY_ADMIN_TOKEN` - токен для записи JSON через API

## Важно

JSON-файлы лежат в `data/`. Если не подключить persistent disk, изменения на free-хостинге Render могут не пережить redeploy.
