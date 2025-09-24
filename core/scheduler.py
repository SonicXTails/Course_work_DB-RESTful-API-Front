import os, time, logging, traceback
from datetime import timedelta
from threading import Thread

from django.db import transaction
from django.utils import timezone

from core.models import BackupConfig, BackupFile
from core.utils.backups import create_sql_backup

log = logging.getLogger(__name__)

SLEEP_SEC = 30         # как часто проверяем
RETENTION_DAYS = 14    # фиксированный срок хранения

def _cleanup_old_files():
    """Удалить успешные бэкапы старше RETENTION_DAYS (и записи)."""
    cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
    qs = BackupFile.objects.filter(
        status=BackupFile.Status.SUCCESS,
        created_at__lt=cutoff
    )
    for b in qs.iterator():
        try:
            if b.file_path and os.path.exists(b.file_path):
                os.remove(b.file_path)
        except Exception:
            pass
        try:
            b.delete()
        except Exception:
            pass

def _due_now_and_mark():
    """
    Возвращает True один раз в сутки после наступления 00:00 локальной TZ.
    Блокировка через select_for_update, чтобы только один воркер стартовал.
    """
    with transaction.atomic():
        cfg, _ = BackupConfig.objects.select_for_update().get_or_create(
            pk=1, defaults={"last_run_at": None}
        )
        now = timezone.localtime()  # локальная таймзона проекта
        last = timezone.localtime(cfg.last_run_at) if cfg.last_run_at else None

        already_today = (last is not None and last.date() == now.date())

        # Строго после наступления 00:00, и ещё не бежали сегодня
        if already_today or now.hour != 0:
            return False

        # помечаем «взяли слот» — больше никто не побежит сегодня
        cfg.last_run_at = timezone.now()
        cfg.save(update_fields=["last_run_at"])
        return True

def _tick_once():
    if not _due_now_and_mark():
        return
    try:
        b = create_sql_backup(initiator=None)
        _cleanup_old_files()
        if b.status != BackupFile.Status.SUCCESS:
            log.error("Backup failed: %s", b.log)
    except Exception as e:
        log.exception("Backup job crashed: %s", e)

def _loop():
    while True:
        try:
            _tick_once()
        except Exception:
            log.error("Scheduler tick error:\n%s", traceback.format_exc())
        time.sleep(SLEEP_SEC)

def start_scheduler_thread():
    """
    Запускаем фоновый daemon-поток. Защита от двойного старта runserver.
    """
    # Эти переменные ставит Django/gunicorn/uvicorn во «втором» процессе;
    # просто запускаем — защита выше, на уровне select_for_update.
    thr = Thread(target=_loop, name="backup-scheduler", daemon=True)
    thr.start()