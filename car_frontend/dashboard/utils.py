from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

DENY_GROUPS = {"admin", "administrator", "администратор", "analyst", "analitic", "аналитик"}

def deny_admin_analyst(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.is_authenticated:
            try:
                group_names = {g.name.lower() for g in u.groups.all()}
            except Exception:
                group_names = set()
            roles = set(getattr(u, "roles", []))

            if u.is_staff or u.is_superuser or group_names & DENY_GROUPS or roles & {"admin", "analyst", "analitic"}:
                messages.warning(request, "Доступ к разделу заказов закрыт для администратора и аналитика.")
                return redirect("users_dashboard")

        return view_func(request, *args, **kwargs)
    return _wrapped