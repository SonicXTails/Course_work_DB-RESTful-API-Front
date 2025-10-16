from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        try:
            from .scheduler import start_scheduler_thread
            start_scheduler_thread()
        except Exception:
            pass

        try:
            from . import signals
        except Exception:
            pass