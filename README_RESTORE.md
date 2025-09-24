# Сценарий восстановления (restore) PostgreSQL

Этот пакет содержит готовые скрипты восстановления БД из бэкапа **plain SQL (.sql.gz)**
и быструю проверку целостности.

## Состав
- `restore.sh` — Bash-скрипт для Linux/macOS (локальный PostgreSQL).
- `restore.ps1` — PowerShell-скрипт для Windows.
- `verify.sql` — SQL-проверки после восстановления.

> Если бэкап у тебя в формате *custom* (`.dump`), используй `pg_restore` вместо `psql`:
> `pg_restore -d <DB> -c -j 4 <file.dump>` и пропусти распаковку gzip.

## 1) Подготовка
1. Установи клиентские утилиты PostgreSQL: `psql`, `pg_dump` (обычно в пакете `postgresql-client`).
2. Узнай или задай параметры подключения: хост, порт, пользователь. Пароль передаётся через `PGPASSWORD`.
3. Помести бэкап `*.sql.gz` в папку `./backups` (или укажи путь ключом `-f`).

## 2) Имитация сбоя (опционально, для демонстрации)
```sql
-- примитивный "сбой": удалим БД или критичную таблицу
DROP DATABASE IF EXISTS api_car;
-- либо:
-- DROP TABLE IF EXISTS public.cars;
```
Задача restore — вернуть систему в рабочее состояние **из бэкапа**.

## 3) Восстановление (Linux/macOS)
```bash
cd /mnt/data/restore
export PGPASSWORD='секретный_пароль'
# Вариант 1: указать конкретный файл
./restore.sh -d api_car -f backups/2025-09-01_03-00.sql.gz -U appuser -h 127.0.0.1 -p 5432 -y
# Вариант 2: взять самый свежий из ./backups
./restore.sh -d api_car -U appuser -y
```

## 4) Восстановление (Windows PowerShell)
```powershell
cd /mnt/data/restore
$env:PGPASSWORD = "секретный_пароль"
.\restore.ps1 -DbName api_car -BackupFile .\backups\2025-09-01_03-00.sql.gz -User appuser -Host 127.0.0.1 -Port 5432
# или без указания файла — возьмётся самый свежий
.\restore.ps1 -DbName api_car -User appuser
```

## 5) Проверка целостности
Скрипты **автоматически** запускают `verify.sql`. Он:
- печатает топ-таблиц по размеру и приблизительное число строк;
- валидирует наличие ключевых таблиц;
- делает несколько выборочных проверок внешних ключей;
- проверяет наличие представлений `vw_active_listings`, `vw_sales_by_make_month`, `vw_user_activity`.

При необходимости отредактируй список сущностей под свою схему.

## 6) Восстановление в Docker
Если PostgreSQL запущен в Docker-контейнере, то есть три пути:

**A. Вызов psql с хоста (проброшен порт 5432):**
```bash
export PGPASSWORD='секрет'
./restore.sh -d api_car -f backups/last.sql.gz -h 127.0.0.1 -p 5432 -U appuser -y
```

**B. Копирование бэкапа в контейнер и restore внутри контейнера:**
```bash
CONTAINER=pgdb
docker cp backups/last.sql.gz "$CONTAINER:/tmp/last.sql.gz"
docker exec -e PGPASSWORD=secret -it "$CONTAINER" bash -lc \
  "gzip -dc /tmp/last.sql.gz | psql -U appuser -d postgres -c \"DROP DATABASE IF EXISTS api_car;\" && \
   psql -U appuser -d postgres -c \"CREATE DATABASE api_car OWNER appuser;\" && \
   gzip -dc /tmp/last.sql.gz | psql -U appuser -d api_car && \
   psql -U appuser -d api_car -f /tmp/verify.sql"
```

**C. `docker-compose exec` (аналогично B):**
```bash
docker-compose exec -e PGPASSWORD=secret db bash -lc "gzip -dc /backups/last.sql.gz | psql -U appuser -d api_car"
```

## 7) После восстановления
1. Прогони миграции приложения (на случай несовпадения версий схемы с кодом):
   - Django: `python manage.py migrate`.
2. Перегенерируй материализованные представления (если используются).
3. Перезапусти API/веб:
   - `systemctl restart api` / `docker compose restart api`
4. Зайди в приложение под **администратором** и визуально проверь ключевые экраны.

## 8) Типичные ошибки и решения
- *FATAL: database "..." is being accessed by other users* — скрипт уже делает `pg_terminate_backend`, но проверь активные коннекты/пулы.
- *permission denied* — у пользователя нет прав на `DROP/CREATE DATABASE`. Выполни под суперпользователем или заранее создай пустую БД и передай `--no-drop`.
- Бэкап **в формате custom** (`.dump`) — используй `pg_restore`:
  ```bash
  createdb api_car
  pg_restore -d api_car -c -j 4 last.dump
  ```

---

Готово. Этот сценарий покрывает демонстрацию **restore на учебном стенде** и проверку целостности.