from decimal import Decimal
from typing import Any

from django.shortcuts import render, redirect
from django.utils.dateparse import parse_datetime
from django.contrib import messages
from django.utils.timezone import localtime

from .decorators import token_required
from .common import (
    BOOTSTRAP_URL, ORDERS_URL, _get_json, _post_json, _safe_json, STATUS_MAP_RU
)
from .roles import is_admin, is_analitic

ORDER_STATUS_RU = {
    "pending":   "ожидает оплаты",
    "reserved":  "зарезервировано",
    "confirmed": "подтверждён",
    "canceled":  "отменён",   # синоним
    "cancelled": "отменён",
    "completed": "завершён",
}

def _as_list(maybe) -> list[dict[str, Any]]:
    """Унифицируем ответ API: list или {results: []} → list."""
    if isinstance(maybe, list):
        return maybe
    if isinstance(maybe, dict) and isinstance(maybe.get("results"), list):
        return maybe["results"]
    return []

def _norm_status(val: Any) -> str:
    """Приводим статус к единому виду (cancelled)."""
    s = str(val or "").lower().strip()
    return "cancelled" if s == "canceled" else s

def orders_view(request):
    token = request.session.get("api_token")
    if not token:
        return redirect("auth")

    # Для админа/аналитика просто покажем уведомление (без редиректа).
    if is_admin(request) or is_analitic(request):
        messages.warning(request, "Раздел «Мои заказы» предназначен для покупателей.")

    # Базовые данные для подписей авто
    boot = _get_json(BOOTSTRAP_URL, token, timeout=8) or {}
    me    = boot.get("me") or {}
    cars  = boot.get("cars") or []
    makes = {m["id"]: m["name"] for m in (boot.get("makes") or [])}
    models= {m["id"]: m["name"] for m in (boot.get("models") or [])}

    by_vin = {str(c.get("VIN")): c for c in cars}
    by_id  = {str(c.get("id")):  c for c in cars}

    # Тянем заказы и оставляем только «мои»
    data_orders = _get_json(ORDERS_URL, token, timeout=8) or []
    all_orders  = _as_list(data_orders)
    my_id = me.get("id")
    orders = [
        o for o in all_orders
        if (o.get("buyer") == my_id)
        or (o.get("user") == my_id)
        or (o.get("author") == my_id)
    ]

    # --------- ФИЛЬТРЫ ПО СТАТУСУ ----------
    # Принимаем ?status=pending&status=reserved или ?status=pending,reserved
    selected = set()
    for v in request.GET.getlist("status"):
        for part in str(v).split(","):
            part = part.strip().lower()
            if part:
                selected.add(_norm_status(part))

    if selected:
        orders = [o for o in orders if _norm_status(o.get("status")) in selected]
    else:
        # По умолчанию скрываем отменённые
        orders = [o for o in orders if _norm_status(o.get("status")) != "cancelled"]

    status_choices = [
        ("pending",   ORDER_STATUS_RU["pending"]),
        ("reserved",  ORDER_STATUS_RU["reserved"]),
        ("confirmed", ORDER_STATUS_RU["confirmed"]),
        ("completed", ORDER_STATUS_RU["completed"]),
        ("cancelled", ORDER_STATUS_RU["cancelled"]),
    ]
    # ----------------------------------------

    # Обогащаем карточкой авто и форматами
    for o in orders:
        car_ref = o.get("car")
        vin = None
        car_obj = None

        if isinstance(car_ref, dict):
            vin = car_ref.get("VIN") or car_ref.get("vin")
            cid = car_ref.get("id")
            if vin and str(vin) in by_vin:
                car_obj = by_vin[str(vin)]
            elif cid and str(cid) in by_id:
                car_obj = by_id[str(cid)]
        else:
            if car_ref is not None and str(car_ref) in by_vin:
                car_obj = by_vin[str(car_ref)]
                vin = car_obj.get("VIN")
            elif car_ref is not None and str(car_ref) in by_id:
                car_obj = by_id[str(car_ref)]
                vin = car_obj.get("VIN")

        o["_car"] = car_obj
        o["car_vin"] = vin or (car_obj.get("VIN") if car_obj else None)

        if car_obj:
            mk = makes.get(car_obj.get("make")) or ""
            md = models.get(car_obj.get("model")) or ""
            yr = car_obj.get("year") or ""
            o["car_title"] = f"{mk} {md}".strip() + (f" · {yr}" if yr else "")
            try:
                price_int = int(Decimal(str(car_obj.get("price") or 0)))
                o["car_price_fmt"] = f"{price_int:,}".replace(",", " ")
            except Exception:
                o["car_price_fmt"] = str(car_obj.get("price") or "—")
            o["car_status_ru"] = STATUS_MAP_RU.get(str(car_obj.get("status") or "").lower(), car_obj.get("status") or "—")
        else:
            o["car_title"] = "Авто"
            o["car_price_fmt"] = "—"
            o["car_status_ru"] = "—"

        st_norm = _norm_status(o.get("status"))
        o["status"] = st_norm
        o["status_ru"] = ORDER_STATUS_RU.get(st_norm, o.get("status") or "—")

        dt = parse_datetime(o.get("created_at") or "") or parse_datetime(o.get("created") or "")
        dt_local = localtime(dt) if dt else None
        o["created_at_fmt"] = dt_local.strftime("%d.%m.%Y %H:%M") if dt_local else "—"

    # Свежие сверху (по строке — достаточно для «человеческой» сортировки)
    orders.sort(key=lambda x: x.get("created_at_fmt") or "", reverse=True)

    return render(request, "dashboard/orders.html", {
        "orders": orders,
        "status_choices": status_choices,
        "selected_statuses": sorted(selected),
    })

@token_required
def order_confirm(request, order_id):
    # Запрещаем действие для админа/аналитика
    if is_admin(request) or is_analitic(request):
        messages.warning(request, "Подтверждение заказов недоступно для администратора и аналитика.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    url  = f"{ORDERS_URL}{order_id}/confirm/"
    resp = _post_json(url, request.session.get("api_token"), timeout=10)
    data = _safe_json(resp)

    if getattr(resp, "status_code", 400) in (200, 201):
        messages.success(request, f"Транзакция создана (#{data.get('id')}). Заказ подтверждён.")
    else:
        messages.error(request, data.get("detail") or "Не удалось подтвердить заказ.")
    return redirect(request.META.get("HTTP_REFERER", "/orders/"))

@token_required
def order_seller_cancel(request, order_id):
    # Запрещаем действие для админа/аналитика
    if is_admin(request) or is_analitic(request):
        messages.warning(request, "Отмена заказов недоступна для администратора и аналитика.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    payload = {}
    reason = (request.POST.get("reason") or "").strip()
    if reason:
        payload["reason"] = reason

    url  = f"{ORDERS_URL}{order_id}/seller_cancel/"
    resp = _post_json(url, request.session.get("api_token"), json=payload, timeout=10)
    data = _safe_json(resp)
    if getattr(resp, "status_code", 400) in (200, 204):
        messages.success(request, f"Заказ #{order_id} отменён.")
    else:
        messages.error(request, data.get("detail") or "Не удалось отменить заказ.")
    return redirect(request.META.get("HTTP_REFERER", "/orders/"))

@token_required
def order_buyer_cancel(request, order_id: int):
    """Отмена со стороны покупателя (buyer_cancel, при 404 — fallback на /cancel/)."""
    if is_admin(request) or is_analitic(request):
        messages.warning(request, "Отмена недоступна для администратора и аналитика.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    payload = {}
    reason = (request.POST.get("reason") or "").strip()
    if reason:
        payload["reason"] = reason

    # основной эндпоинт
    url = f"{ORDERS_URL}{order_id}/buyer_cancel/"
    resp = _post_json(url, request.session.get("api_token"), json=payload, timeout=10)
    if getattr(resp, "status_code", 400) in (200, 204):
        messages.success(request, f"Заказ #{order_id} отменён.")
        return redirect(request.META.get("HTTP_REFERER", "/orders/"))

    # fallback
    if getattr(resp, "status_code", 0) == 404:
        resp2 = _post_json(f"{ORDERS_URL}{order_id}/cancel/", request.session.get("api_token"), json=payload, timeout=10)
        if getattr(resp2, "status_code", 400) in (200, 204):
            messages.success(request, f"Заказ #{order_id} отменён.")
            return redirect(request.META.get("HTTP_REFERER", "/orders/"))
        data2 = _safe_json(resp2)
        messages.error(request, data2.get("detail") or f"Не удалось отменить заказ (HTTP {getattr(resp2, 'status_code', '???')}).")
        return redirect(request.META.get("HTTP_REFERER", "/orders/"))

    data = _safe_json(resp)
    messages.error(request, data.get("detail") or f"Не удалось отменить заказ (HTTP {getattr(resp, 'status_code', '???')}).")
    return redirect(request.META.get("HTTP_REFERER", "/orders/"))