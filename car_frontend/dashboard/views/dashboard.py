from decimal import Decimal
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime

from .common import BOOTSTRAP_URL, _get_json, _qs_without, status_ru
from .roles import _is_admin_or_analitic_session

def users_dashboard(request):
    token = request.session.get("api_token")
    data  = _get_json(BOOTSTRAP_URL, token, timeout=8) if token else None

    user_data = (data or {}).get("me")
    makes     = (data or {}).get("makes", [])
    models    = (data or {}).get("models", [])
    cars      = (data or {}).get("cars", [])
    imgs      = (data or {}).get("car_images", [])

    makes_map  = {m["id"]: m["name"] for m in makes}
    models_map = {m["id"]: {"name": m["name"], "make": m["make"]} for m in models}

    images_by_car = {}
    for img in imgs:
        images_by_car.setdefault(str(img.get("car")), []).append(img.get("image"))

    for c in cars:
        c["make_name"] = makes_map.get(c.get("make")) or "—"
        model_id = c.get("model")
        c["model_name"] = models_map.get(model_id, {}).get("name", "—")

        imgs_car = images_by_car.get(str(c.get("VIN"))) or images_by_car.get(str(c.get("id"))) or []
        c["images"] = imgs_car

        first = c.get("seller_first_name") or ""
        last  = c.get("seller_last_name") or ""
        c["seller_full_name"] = (f"{first} {last}".strip() or str(c.get("seller") or "—"))

        c["status_ru"] = status_ru(c.get("status"))

        dt = parse_datetime(c.get("created_at") or "")
        c["_created_dt"] = localtime(dt) if dt else None
        c["created_at_fmt"] = c["_created_dt"].strftime("%d.%m.%Y %H:%M") if c["_created_dt"] else "—"

        try:
            c["_price_int"] = int(Decimal(str(c.get("price") or 0)))
        except Exception:
            c["_price_int"] = None
        c["price_fmt"] = (
            f"{c['_price_int']:,}".replace(",", " ")
            if c["_price_int"] is not None else str(c.get("price", "0"))
        )

        try:
            c["_year_int"] = int(c.get("year")) if c.get("year") is not None else None
        except Exception:
            c["_year_int"] = None

    g = request.GET
    q          = (g.get('q') or '').strip().lower()
    status_f   = (g.get('status') or '').strip().lower()
    year_min   = g.get('year_min')
    year_max   = g.get('year_max')
    price_min  = g.get('price_min')
    price_max  = g.get('price_max')
    sort       = g.get('sort')

    def _passes(c):
        if q:
            hay = " ".join([
                str(c.get("make_name") or ""),
                str(c.get("model_name") or ""),
                str(c.get("VIN") or ""),
            ]).lower()
            if q not in hay:
                return False
        if status_f and (str(c.get("status") or "").lower() != status_f):
            return False
        if year_min:
            try:
                if (c.get("_year_int") or -10**9) < int(year_min): return False
            except Exception:
                pass
        if year_max:
            try:
                if (c.get("_year_int") or 10**9) > int(year_max): return False
            except Exception:
                pass
        if price_min:
            try:
                if (c.get("_price_int") or -10**12) < int(price_min): return False
            except Exception:
                pass
        if price_max:
            try:
                if (c.get("_price_int") or 10**12) > int(price_max): return False
            except Exception:
                pass
        return True

    cars = [c for c in cars if _passes(c)]

    if sort == "new":
        cars.sort(key=lambda x: (x.get("_created_dt") is None, -(x["_created_dt"].timestamp() if x.get("_created_dt") else 0)))
    elif sort == "old":
        cars.sort(key=lambda x: (x.get("_created_dt") is None, x["_created_dt"].timestamp() if x.get("_created_dt") else float("inf")))
    elif sort == "price_asc":
        cars.sort(key=lambda x: (x.get("_price_int") is None, x.get("_price_int") if x.get("_price_int") is not None else float("inf")))
    elif sort == "price_desc":
        cars.sort(key=lambda x: (x.get("_price_int") is None, -(x.get("_price_int") if x.get("_price_int") is not None else -10**12)))
    elif sort == "year_asc":
        cars.sort(key=lambda x: (x.get("_year_int") is None, x.get("_year_int") if x.get("_year_int") is not None else float("inf")))
    elif sort == "year_desc":
        cars.sort(key=lambda x: (x.get("_year_int") is None, -(x.get("_year_int") if x.get("_year_int") is not None else -10**6)))

    paginator = Paginator(cars, 10)
    page_obj = paginator.get_page(g.get('page'))

    base_qs         = _qs_without(g, 'page')
    qs_no_q         = _qs_without(g, 'page', q='')
    qs_no_status    = _qs_without(g, 'page', status='')
    qs_no_year_min  = _qs_without(g, 'page', year_min='')
    qs_no_year_max  = _qs_without(g, 'page', year_max='')
    qs_no_price_min = _qs_without(g, 'page', price_min='')
    qs_no_price_max = _qs_without(g, 'page', price_max='')
    qs_no_sort      = _qs_without(g, 'page', sort='')

    can_reserve = not _is_admin_or_analitic_session(request)

    return render(request, "dashboard/index.html", {
        "user": user_data,
        "cars": page_obj.object_list,
        "page_obj": page_obj,
        "base_qs": base_qs,
        "qs_no_q": qs_no_q,
        "qs_no_status": qs_no_status,
        "qs_no_year_min": qs_no_year_min,
        "qs_no_year_max": qs_no_year_max,
        "qs_no_price_min": qs_no_price_min,
        "qs_no_price_max": qs_no_price_max,
        "qs_no_sort": qs_no_sort,
        "CAN_RESERVE": can_reserve,
    })
