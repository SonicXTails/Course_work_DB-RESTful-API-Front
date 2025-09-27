from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from .decorators import token_required
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime

from .common import API_URL, BOOTSTRAP_URL, CARS_URL, _get_json, _post_json, _safe_json, _h, status_ru
from .roles import _is_admin_or_analitic_session

def car_detail(request, vin):
    token = request.session.get("api_token")
    data  = _get_json(BOOTSTRAP_URL, token, timeout=8) if token else None
    me    = (data or {}).get("me")

    makes_map  = {m["id"]: m["name"] for m in (data or {}).get("makes", [])}
    models_map = {m["id"]: {"name": m["name"], "make": m["make"]} for m in (data or {}).get("models", [])}

    images_by_car = {}
    for img in (data or {}).get("car_images", []):
        images_by_car.setdefault(str(img.get("car")), []).append(img.get("image"))

    car, not_found = None, False
    import requests
    resp = requests.Session().get(f"{CARS_URL}{vin}/", headers=_h(token), timeout=6)
    if resp.ok:
        car = resp.json()
    else:
        not_found = True

    seller_reviews = []
    seller_rating_avg = None
    seller_rating_count = 0
    my_already_reviewed = False
    can_review = False

    if car:
        car["make_name"]  = makes_map.get(car.get("make")) or "—"
        model_id = car.get("model")
        car["model_name"] = models_map.get(model_id, {}).get("name", "—")
        car["images"]     = images_by_car.get(str(car.get("VIN"))) or []

        first = car.get("seller_first_name") or ""
        last  = car.get("seller_last_name") or ""
        car["seller_full_name"] = (f"{first} {last}".strip() or str(car.get("seller")))

        dt = parse_datetime(car.get("created_at") or "")
        car["created_at_fmt"] = localtime(dt).strftime("%d.%m.%Y %H:%M") if dt else "—"

        try:
            price_int = int(Decimal(str(car.get("price", "0"))))
            car["price_fmt"] = f"{price_int:,}".replace(",", " ")
        except Exception:
            car["price_fmt"] = str(car.get("price", "0"))

        seller_id = car.get("seller")
        if seller_id and token:
            r_reviews = _get_json(f"{API_URL}reviews/", token, timeout=6) or []
            seller_reviews = [rv for rv in r_reviews if rv.get("target") == seller_id]
            ratings = [int(rv.get("rating", 0)) for rv in seller_reviews if rv.get("rating") is not None]
            if ratings:
                seller_rating_count = len(ratings)
                seller_rating_avg = round(sum(ratings) / seller_rating_count, 1)
            if me:
                my_already_reviewed = any((rv.get("author") == me.get("id")) for rv in seller_reviews)
            can_review = bool(me and seller_id and me.get("id") != seller_id and not my_already_reviewed)

    return render(request, "dashboard/car_detail.html", {
        "car": car,
        "vin": vin,
        "not_found": not_found,
        "me": me,
        "seller_reviews": seller_reviews,
        "seller_rating_avg": seller_rating_avg,
        "seller_rating_count": seller_rating_count,
        "can_review": can_review,
        "my_already_reviewed": my_already_reviewed,
    })

@token_required
def car_reserve(request, vin):
    """Кнопка «Зарезервировать» на карточке авто."""
    if _is_admin_or_analitic_session(request):
        messages.warning(request, "Резерв недоступен для администратора и аналитика.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    url  = f"{CARS_URL}{vin}/reserve/"
    resp = _post_json(url, request.session.get("api_token"), timeout=10)
    data = _safe_json(resp)
    if getattr(resp, "status_code", 400) in (200, 201):
        messages.success(request, f"Заказ создан (#{data.get('id')}). Авто зарезервировано.")
    else:
        messages.error(request, data.get("detail") or "Не удалось зарезервировать авто.")
    return redirect(request.META.get("HTTP_REFERER", "/"))
