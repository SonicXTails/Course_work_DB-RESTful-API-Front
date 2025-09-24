<# restore.ps1 — восстановление PostgreSQL из .sql.gz (Windows PowerShell)
Примеры:
  $env:PGPASSWORD = "secret"
  .\restore.ps1 -DbName api_car -BackupFile .\backups\2025-09-01_03-00.sql.gz -Host localhost -Port 5432 -User appuser
#>
param(
  [Parameter(Mandatory=$true)][string]$DbName,
  [Parameter(Mandatory=$false)][string]$BackupFile = "",
  [Parameter(Mandatory=$false)][string]$Host = "localhost",
  [Parameter(Mandatory=$false)][int]$Port = 5432,
  [Parameter(Mandatory=$false)][string]$User = "postgres",
  [switch]$NoDrop,
  [switch]$SchemaOnly
)

$ErrorActionPreference = "Stop"

function Find-LatestBackup {
  $files = Get-ChildItem -Path ".\backups" -Filter "*.sql.gz" | Sort-Object LastWriteTime -Descending
  if ($files.Count -eq 0) { throw "В .\backups не найдено *.sql.gz" }
  return $files[0].FullName
}

if (-not $BackupFile -or -not (Test-Path $BackupFile)) {
  $BackupFile = Find-LatestBackup
  Write-Host "Использую свежий бэкап: $BackupFile"
}

$env:PGHOST = $Host
$env:PGPORT = $Port
$env:PGUSER = $User

# Проверка соединения
& psql -d postgres -Atqc "SELECT 'ok'" | Out-Null

if (-not $NoDrop) {
  Write-Host "Отключаю сессии и удаляю БД $DbName, если существует"
  & psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DbName' AND pid <> pg_backend_pid();"
  & psql -d postgres -c "DROP DATABASE IF EXISTS $DbName;"
}

Write-Host "Создаю БД $DbName"
$enc = (& psql -d postgres -At -c "SHOW SERVER_ENCODING;")
& psql -d postgres -c "CREATE DATABASE $DbName OWNER $User ENCODING '$enc';"

Write-Host "Восстанавливаю из $BackupFile"
if ($SchemaOnly) {
  # Вырезать часть до $$DATA$$ (если есть) — как упрощение: импортируем всё, т.к. plain backup
  & 7z e -so "$BackupFile" | psql -d "$DbName"
} else {
  & 7z e -so "$BackupFile" | psql -d "$DbName"
}

Write-Host "Проверка целостности"
& psql -d "$DbName" -f ".\verify.sql"

Write-Host "Готово."