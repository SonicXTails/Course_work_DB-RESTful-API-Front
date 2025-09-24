
#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-api_car}"
PGUSER="${PGUSER:-postgres}"
PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
BACKUP="${BACKUP:-../restore/backups/last.sql.gz}"

echo "==> Имитация сбоя: дроп БД ${DB_NAME}"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"

echo "==> Восстановление"
pushd ../restore >/dev/null
./restore.sh -d "${DB_NAME}" -f "${BACKUP}" -y
popd >/dev/null

echo "==> Проверка завершена"
