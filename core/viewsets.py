import os, shutil
from rest_framework.viewsets import ModelViewSet
from core.middleware import set_current_user, clear_current_user
from rest_framework.permissions import IsAdminUser
from django.http import FileResponse, Http404
from core.models import BackupFile
from core.serializers import BackupFileSerializer
from core.utils.backups import create_sql_backup
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import serializers
from core.models import BackupFile, BackupConfig

class AuditModelViewSet(ModelViewSet):
    """
    Кладёт аутентифицированного DRF-пользователя в thread-local ПОСЛЕ authentication.
    """
    def initial(self, request, *args, **kwargs):
        resp = super().initial(request, *args, **kwargs)
        set_current_user(getattr(self.request, "user", None))
        return resp

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            return super().finalize_response(request, response, *args, **kwargs)
        finally:
            clear_current_user()

class BackupViewSet(ModelViewSet):
    queryset = BackupFile.objects.all()
    serializer_class = BackupFileSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        b = create_sql_backup(initiator=request.user if request.user.is_authenticated else None)
        ser = self.get_serializer(b)
        status_code = 201 if b.status == BackupFile.Status.SUCCESS else 500
        return Response(ser.data, status=status_code)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        b = self.get_object()
        if b.status != BackupFile.Status.SUCCESS or not b.file_path or not os.path.exists(b.file_path):
            raise Http404("Файл недоступен")
        fname = os.path.basename(b.file_path)
        return FileResponse(open(b.file_path, "rb"), as_attachment=True, filename=fname)
    
    @action(detail=False, methods=["get", "put", "post"], url_path="config")
    def config(self, request):
        from django.conf import settings
        cfg, _ = BackupConfig.objects.get_or_create(
            pk=1,
            defaults={
                "scheduler_enabled": False,
                "cron": os.getenv("BACKUPS_CRON", "0 3 * * *"),
                "retention_days": int(os.getenv("BACKUPS_RETENTION_DAYS", str(getattr(settings, "BACKUPS_RETENTION_DAYS", 14)))),
            },
        )

        current = {
            "scheduler_enabled": bool(cfg.scheduler_enabled),
            "cron": cfg.cron,
            "retention_days": cfg.retention_days,
            "backups_dir": settings.BACKUPS_DIR,
            "pg_dump_path": settings.PG_DUMP_PATH or (shutil.which("pg_dump") or ""),
        }
        if request.method == "GET":
            return Response(current)

        class _CfgSer(serializers.Serializer):
            scheduler_enabled = serializers.BooleanField(required=False)
            cron = serializers.RegexField(r"^[^\n\r]{3,64}$", required=False)
            retention_days = serializers.IntegerField(required=False, min_value=1, max_value=365)

        s = _CfgSer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)

        data = s.validated_data
        if "scheduler_enabled" in data:
            cfg.scheduler_enabled = data["scheduler_enabled"]
        if "cron" in data:
            cfg.cron = data["cron"]
        if "retention_days" in data:
            cfg.retention_days = data["retention_days"]
        cfg.save()

        os.environ["ENABLE_BACKUPS_SCHEDULER"] = "1" if cfg.scheduler_enabled else "0"
        os.environ["BACKUPS_CRON"] = cfg.cron
        os.environ["BACKUPS_RETENTION_DAYS"] = str(cfg.retention_days)

        return Response({
            "scheduler_enabled": cfg.scheduler_enabled,
            "cron": cfg.cron,
            "retention_days": cfg.retention_days,
            "backups_dir": settings.BACKUPS_DIR,
            "pg_dump_path": settings.PG_DUMP_PATH or (shutil.which("pg_dump") or ""),
        }, status=200)