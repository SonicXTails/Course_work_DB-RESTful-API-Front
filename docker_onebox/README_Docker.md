# API_CAR_DASHBOARD — запуск через Docker (API + Front в одном контейнере)

> **Коротко:** образ собираем один раз, запускаем контейнер с пробросом портов `8000` (API) и `8001` (Front).  
> База может быть либо на твоём компьютере (Windows/macOS/Linux), либо в отдельном контейнере Postgres.

---

## ⚡ TL;DR

```powershell
# 1) Сборка (из корня проекта)
docker build -f docker_onebox\Dockerfile -t car-onebox:latest .

# 2) Запуск (Windows PowerShell, БД на хосте)
docker run --name car-onebox --env-file .\.env -e DB_HOST=host.docker.internal -p 8000:8000 -p 8001:8001 car-onebox:latest

# 3) Открыть в браузере
# Front:  http://127.0.0.1:8001/
# API:    http://127.0.0.1:8000/swagger/
# Admin:  http://127.0.0.1:8000/admin/
```

👉 Если БД в отдельном контейнере — см. раздел **«Postgres в Docker»** ниже.

---

## Требования

- Docker Desktop / Docker Engine
- Файл `.env` в корне проекта (см. пример ниже)
- Postgres (на твоём ПК **или** в отдельном контейнере)

---

## Что уже есть в репозитории (Docker One-Box)

В проекте используется «one-box» контейнер, который поднимает **API и Front** вместе под управлением **supervisor**:

```
docker_onebox/
├─ Dockerfile
├─ entrypoint.sh
└─ supervisord.conf
```

- API (Django) — порт **8000** (в DEV по умолчанию через `runserver`)
- Front (Django UI) — порт **8001** (через `runserver`)

> Прод-вариант с Nginx/`gunicorn` можно добавить отдельно (см. «Продакшен»).

---

## .env (пример)

> Важно: строки без кавычек. Ключ `FERNET_KEY` — **без** `'` и `"`.

```env
DJANGO_SECRET_KEY=-^2c$5384oas-!$i2t%*7itv9=e6e2)wgp3o*oa9!e68qpzaff
DEBUG=1

ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8001,http://localhost:8001
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8001,http://localhost:8001

DB_NAME=DB_Car_dash
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost         # если БД на хосте Windows/macOS/Linux — см. «Запуск» ниже
DB_PORT=5432
DB_CONN_MAX_AGE=60

FERNET_KEY=3FN4cvmJjVFQO2ekJAy308jcpu8E2CyV80Z7UPgxcxM=

# (опционально) суперпользователь
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin123
```

---

## Сборка образа

**Windows PowerShell**
```powershell
cd C:\API_CAR_DASHBOARD
docker build -f docker_onebox\Dockerfile -t car-onebox:latest .
```

**Linux/macOS (bash)**
```bash
cd ./API_CAR_DASHBOARD
docker build -f docker_onebox/Dockerfile -t car-onebox:latest .
```

---

## Запуск контейнера (БД на хост-машине)

> Внутри контейнера `localhost` — это сам контейнер. Чтобы достучаться до твоего ПК:
> - **Windows/macOS (Docker Desktop):** используй `host.docker.internal`
> - **Linux:** укажи IP/hostname твоей машины (например, `192.168.1.10`)

### Windows PowerShell
```powershell
docker rm -f car-onebox 2>$null
docker run --name car-onebox `
  --env-file .\.env `
  -e DB_HOST=host.docker.internal `
  -p 8000:8000 `
  -p 8001:8001 `
  car-onebox:latest
```

### Linux/macOS (bash)
```bash
docker rm -f car-onebox 2>/dev/null || true
docker run --name car-onebox   --env-file ./.env   -e DB_HOST=host.docker.internal   -p 8000:8000   -p 8001:8001   car-onebox:latest
```

> Если на Linux `host.docker.internal` недоступен — поставь вместо него IP твоего хоста, например: `-e DB_HOST=192.168.1.10`.

После старта открывай:
- Front: **http://127.0.0.1:8001/**
- API (Swagger): **http://127.0.0.1:8000/swagger/**
- Admin: **http://127.0.0.1:8000/admin/**

---

## Альтернатива: Postgres в Docker

Подними отдельный контейнер с БД и общую сеть:

```powershell
# общая сеть
docker network create car-net

# Postgres
docker run -d --name car-pg --network car-net `
  -e POSTGRES_DB=DB_Car_dash `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -p 5432:5432 postgres:16

# Приложение (DB_HOST = имя сервиса БД в сети)
docker run --name car-onebox --network car-net `
  --env-file .\.env `
  -e DB_HOST=car-pg `
  -p 8000:8000 -p 8001:8001 `
  car-onebox:latest
```

---

## Команды обслуживания

```powershell
# Логи
docker logs -f car-onebox

# Перезапуск
docker restart car-onebox

# Остановка и удаление
docker rm -f car-onebox
```

---

## Известные нюансы / Траблшутинг

- **Зависает на «Жду Postgres…»**  
  Проверь, что правильно указан `DB_HOST` (см. раздел «Запуск»). Для хостовой БД на Windows/macOS используй `-e DB_HOST=host.docker.internal`.

- **Swagger CSS/JS не грузится (404, MIME text/html)**  
  В DEV текущая конфигурация запускает API через `runserver` — статика отдаётся корректно.  
  Если переключишься на `gunicorn`, нужно включить `whitenoise` и выполнить `collectstatic` в `entrypoint.sh`:
  ```bash
  python manage.py collectstatic --noinput
  ```

- **CRLF в `entrypoint.sh` (ошибка `/bin/bash^M`)**  
  Добавь в `Dockerfile` после COPY:
  ```dockerfile
  RUN sed -i 's/\r$//' /entrypoint.sh && sed -i 's/\r$//' /etc/supervisor/conf.d/supervisord.conf
  ```

- **Порты заняты**  
  Поменяй маппинг, например: `-p 8080:8000 -p 8081:8001`.

- **CORS/CSRF ошибки в браузере**  
  В `.env` должны быть включены `127.0.0.1` и `localhost` на портах `8000` и `8001` в `CORS_ALLOWED_ORIGINS` и `CSRF_TRUSTED_ORIGINS`.

- **`FERNET_KEY` в кавычках**  
  Убирай кавычки в `.env` — иначе ключ будет с символами `'`/`"` внутри и может не подойти.

---

## Продакшен (по желанию)

Для единого адреса (порт 80) и прод-режима можно добавить Nginx внутри контейнера:
- `/api/* → gunicorn :8000`
- `/ → фронт со статики (или :8001)`

Это даст единый URL `http://127.0.0.1/` и правильную раздачу статики без `runserver`. Конфиги можно добавить как второй Dockerfile профиля `prod`.

---

## Порты и сервисы

- `8000` — API (Django, DEV сейчас через `runserver` / можно переключить на `gunicorn`)  
- `8001` — Front (Django UI, DEV через `runserver`)

---