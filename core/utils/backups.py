import os, shutil, gzip, hashlib, datetime, subprocess, tempfile
from django.conf import settings
from django.db import connection
from core.models import BackupFile

def _which_pg_dump():
    if settings.PG_DUMP_PATH:
        return settings.PG_DUMP_PATH
    path = shutil.which("pg_dump")
    if not path:
        raise RuntimeError("pg_dump не найден. Укажи PG_DUMP_PATH в .env или добавь pg_dump в PATH.")
    return path

def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def create_sql_backup(initiator=None) -> BackupFile:
    """
    Создаёт .sql.gz дамп текущей БД через pg_dump.
    Возвращает объект BackupFile со статусом SUCCESS/FAILED.
    """
    db = connection.settings_dict
    name = db["NAME"]; user = db.get("USER") or ""
    password = db.get("PASSWORD") or ""; host = db.get("HOST") or "localhost"
    port = str(db.get("PORT") or "5432")

    b = BackupFile.objects.create(created_by=initiator, method=BackupFile.Method.PG_DUMP, status=BackupFile.Status.PENDING)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_sql = os.path.join(settings.BACKUPS_DIR, f"backup_{name}_{ts}.sql")
    gz_sql  = raw_sql + ".gz"
    cmd = [
        _which_pg_dump(),
        "-h", host, "-p", port, "-U", user, "-d", name,
        "-F", "p", "--no-owner", "--no-privileges"
    ]
    env = {**os.environ, "PGPASSWORD": password}

    try:
        # 1) Снимаем дамп в обычный .sql
        res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if res.returncode != 0:
            b.status = BackupFile.Status.FAILED
            b.log = res.stderr.decode("utf-8", errors="ignore")
            b.save(update_fields=["status", "log"])
            return b

        with open(raw_sql, "wb") as f:
            f.write(res.stdout)

        # 2) Сжимаем в .gz
        with open(raw_sql, "rb") as fin, gzip.open(gz_sql, "wb") as fout:
            shutil.copyfileobj(fin, fout)
        os.remove(raw_sql)

        # 3) Размер и чек-сумма
        size = os.path.getsize(gz_sql)
        sha = _sha256(gz_sql)

        b.file_path = gz_sql
        b.file_size = size
        b.checksum_sha256 = sha
        b.status = BackupFile.Status.SUCCESS
        b.log = "OK"
        b.save(update_fields=["file_path", "file_size", "checksum_sha256", "status", "log"])
        return b
    except Exception as e:
        b.status = BackupFile.Status.FAILED
        b.log = f"EXC: {e}"
        b.save(update_fields=["status", "log"])
        return b