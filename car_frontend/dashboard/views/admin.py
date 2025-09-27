from django.shortcuts import render
from .decorators import admin_required

from .common import ROLES_URL, API_URL, _get_json, _safe_json, _post_json, MAKES_URL

@admin_required
def admin_dashboard_view(request):
    # Базовый каркас. Подробный наполняется в profile_view для админа.
    ctx = {
        "is_admin": True,
        "has_token": bool(request.session.get("api_token")),
        "users": [],
        "roles": [],
        "audit_logs": [],
        "makes": [],
    }
    return render(request, "dashboard/admin.html", ctx)

@admin_required
def make_bulk_reprice(request, make_id):
    from django.contrib import messages
    from django.shortcuts import redirect, render as dj_render

    if request.method == "POST":
        try:
            percent = float(request.POST.get("percent", ""))
        except ValueError:
            messages.error(request, "Процент должен быть числом (можно отрицательное).")
            return redirect(request.META.get("HTTP_REFERER", "/admin/makes/"))

        url  = f"{MAKES_URL}{make_id}/bulk_reprice/"
        resp = _post_json(url, request.session.get("api_token"), json={"percent": percent}, timeout=15)
        data = _safe_json(resp)
        if getattr(resp, "status_code", 400) == 200:
            messages.success(request, f"Цены обновлены: затронуто {data.get('affected')} авто, {percent}%.")
        else:
            messages.error(request, data.get("detail") or "Не удалось пересчитать цены.")
        return redirect(request.META.get("HTTP_REFERER", "/admin/makes/"))

    return dj_render(request, "dashboard/makes_bulk_reprice.html", {"make_id": make_id})
