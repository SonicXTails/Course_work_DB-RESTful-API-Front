from rest_framework.viewsets import ModelViewSet
from core.middleware import set_current_user, clear_current_user

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