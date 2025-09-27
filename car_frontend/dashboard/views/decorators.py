from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .roles import is_admin

def token_required(view):
    @wraps(view)
    def _wrap(request, *args, **kwargs):
        if not request.session.get("api_token"):
            messages.warning(request, "Сначала войди в систему.")
            return redirect("auth")
        return view(request, *args, **kwargs)
    return _wrap

def admin_required(view):
    @wraps(view)
    def _wrap(request, *args, **kwargs):
        if not request.session.get("api_token"):
            messages.warning(request, "Сначала войди в систему.")
            return redirect("auth")
        if not is_admin(request):
            messages.warning(request, "Доступ только для администратора.")
            return redirect("users_dashboard")
        return view(request, *args, **kwargs)
    return _wrap
