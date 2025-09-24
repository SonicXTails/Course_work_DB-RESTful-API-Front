#!/usr/bin/env bash
# restore.sh — восстановление БД PostgreSQL из plain SQL-бэкапа (.sql.gz)
# Использование:
#   ./restore.sh -d <DB_NAME> -f <PATH_TO_BACKUP.sql.gz> [-h <host>] [-p <port>] [-U <user>] [--no-drop]
# Требования: bash, psql, gzip, доступ к БД. Пароль можно передать через переменную окружения PGPASSWORD.
set -euo pipefail

usage() {
  cat <<'EOF'
Восстановление PostgreSQL из .sql.gz (pg_dump --format=plain | gzip).

Параметры:
  -d, --db          Имя базы данных (обязателен)
  -f, --file        Путь к бэкапу .sql.gz (если не задан — берём самый свежий в ./backups)
  -h, --host        Хост PostgreSQL (по умолчанию: localhost)
  -p, --port        Порт PostgreSQL (по умолчанию: 5432)
  -U, --user        Пользователь PostgreSQL (по умолчанию: postgres)
  --no-drop         Не удалять существующую БД (по умолчанию: удаляет и создаёт заново)
  --schema-only     Применить только схему (без данных)
  -y, --yes         Не задавать вопросов (auto-yes)
  -?, --help        Показать помощь

Переменные окружения:
  PGPASSWORD        Пароль пользователя PostgreSQL

Примеры:
  PGPASSWORD=secret ./restore.sh -d api_car -f backups/2025-09-01_03-00.sql.gz -U appuser
  PGPASSWORD=secret ./restore.sh -d api_car -h 127.0.0.1 -p 5432
EOF
}

DB_NAME=""
BACKUP_FILE=""
HOST="localhost"
PORT="5432"
USER="postgres"
NO_DROP="0"
SCHEMA_ONLY="0"
ASSUME_YES="0"

# Парсим аргументы
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--db) DB_NAME="${2:-}"; shift 2 ;;
    -f|--file) BACKUP_FILE="${2:-}"; shift 2 ;;
    -h|--host) HOST="${2:-}"; shift 2 ;;
    -p|--port) PORT="${2:-}"; shift 2 ;;
    -U|--user) USER="${2:-}"; shift 2 ;;
    --no-drop) NO_DROP="1"; shift ;;
    --schema-only) SCHEMA_ONLY="1"; shift ;;
    -y|--yes) ASSUME_YES="1"; shift ;;
    -\?|--help) usage; exit 0 ;;
    *) echo "Неизвестный аргумент: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "${DB_NAME}" ]]; then
  echo "Ошибка: не указано имя БД (-d/--db)"
  usage
  exit 1
fi

# Если не передан файл — возьмём самый новый в ./backups
if [[ -z "${BACKUP_FILE}" ]]; then
  if compgen -G "backups/*.sql.gz" > /dev/null; then
    BACKUP_FILE=$(ls -t backups/*.sql.gz | head -n1)
    echo "BACKUP_FILE не указан. Использую самый свежий: ${BACKUP_FILE}"
  else
    echo "Ошибка: не найдено backups/*.sql.gz, укажи -f/--file"
    exit 1
  fi
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Ошибка: файл бэкапа не найден: ${BACKUP_FILE}"
  exit 1
fi

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "ВНИМАНИЕ: переменная PGPASSWORD не установлена — psql может запросить пароль интерактивно."
fi

echo "==> Начинаю восстановление"
echo "    БД:      ${DB_NAME}"
echo "    Файл:    ${BACKUP_FILE}"
echo "    Хост:    ${HOST}:${PORT}"
echo "    Польз.:  ${USER}"

# Подтверждение
if [[ "${ASSUME_YES}" != "1" ]]; then
  read -p "Продолжить? (y/N) " ans
  if [[ "${ans}" != "y" && "${ans}" != "Y" ]]; then
    echo "Отменено."
    exit 1
  fi
fi

export PGHOST="${HOST}"
export PGPORT="${PORT}"
export PGUSER="${USER}"

# Проверим соединение
psql -d postgres -Atqc "SELECT 'ok'" >/dev/null || { echo "Не удалось подключиться к PostgreSQL"; exit 1; }

# Узнаем владельца/кодировку шаблона
DB_OWNER="${USER}"
DB_ENCODING=$(psql -d postgres -At -c "SHOW SERVER_ENCODING;")

if [[ "${NO_DROP}" != "1" ]]; then
  echo "==> Отключаю активные сессии и удаляю БД '${DB_NAME}' (если существует)"
  psql -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();"
  psql -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${DB_NAME};"
fi

echo "==> Создаю пустую БД '${DB_NAME}' (владелец: ${DB_OWNER}, кодировка: ${DB_ENCODING})"
psql -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_OWNER} ENCODING '${DB_ENCODING}';"

RESTORE_CMD=(psql -d "${DB_NAME}" -v ON_ERROR_STOP=1)

if [[ "${SCHEMA_ONLY}" == "1" ]]; then
  echo "==> Восстанавливаю ТОЛЬКО схему из ${BACKUP_FILE}"
  gzip -dc "${BACKUP_FILE}" | sed -n '1,/$$DATA$$/p' | "${RESTORE_CMD[@]}"
else
  echo "==> Восстанавливаю схему и данные из ${BACKUP_FILE}"
  gzip -dc "${BACKUP_FILE}" | "${RESTORE_CMD[@]}"
fi

echo "==> Выполняю базовую проверку целостности"
psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "$(dirname "$0")/verify.sql"

echo "==> Готово. База '${DB_NAME}' восстановлена из '${BACKUP_FILE}'."