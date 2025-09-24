
# Отказоустойчивость: сценарий сбой → restore
1. Подготовь бэкап `.sql.gz` и положи его в `restore/backups/`.
2. Установи `PGHOST/PGPORT/PGUSER/PGPASSWORD`.
3. Запусти `./resilience_test.sh` — скрипт дропнет БД, восстановит её и прогонит `verify.sql` (внутри restore).
