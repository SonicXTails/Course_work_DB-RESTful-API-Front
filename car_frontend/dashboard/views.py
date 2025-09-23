import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode
from decimal import Decimal
from json import JSONDecodeError

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as dj_logout
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.utils.cache import add_never_cache_headers
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from .forms import ProfileForm

# =========================
# API endpoints
# =========================
API_URL        = "http://localhost:8000/api/v1/"
REGISTER_URL   = f"{API_URL}auth/register/"
TOKEN_URL      = "http://localhost:8000/api-token-auth/"
ME_URL         = f"{API_URL}users/me/"
MAKES_URL      = f"{API_URL}makes/"
MODELS_URL     = f"{API_URL}models/"
CARS_URL       = f"{API_URL}cars/"
CAR_IMAGES_URL = f"{API_URL}car_images/"
USER_ROLES_URL = f"{API_URL}admin/user_roles/"
ROLES_URL      = f"{API_URL}admin/roles/"
ORDERS_URL     = f"{API_URL}orders/"
BOOTSTRAP_URL  = f"{API_URL}bootstrap/"

# =========================
# HTTP session (keep-alive)
# =========================
SESSION = requests.Session()
ADAPTER = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
SESSION.mount("http://", ADAPTER)
SESSION.mount("https://", ADAPTER)

# =========================
# Helpers
# =========================
STATUS_MAP_RU = {
    "available": "продаётся",
    "reserved": "зарезервировано",
    "sold": "продано",
    "unavailable": "недоступно",
}

def status_ru(val: str) -> str:
    return STATUS_MAP_RU.get((val or "").lower(), val or "—")

def _qs_without(original_get, *keys_to_remove, **replacements):
    params = original_get.copy()
    for k in keys_to_remove:
        params.pop(k, None)
    for k, v in replacements.items():
        if v in (None, '', []):
            params.pop(k, None)
        else:
            params[k] = v
    return urlencode(params, doseq=True)

def _h(token: str | None):
    return {"Authorization": f"Token {token}"} if token else {}

def _get_json(url: str, token: str | None, timeout=6):
    try:
        r = SESSION.get(url, headers=_h(token), timeout=timeout)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None

def _post_json(url: str, token: str | None, json=None, data=None, timeout=10):
    try:
        r = SESSION.post(url, headers=_h(token), json=json, data=data, timeout=timeout)
        return r
    except requests.RequestException as _:
        class _Dummy:
            status_code = 599
            def json(self): return {"detail": "network error"}
            text = "network error"
        return _Dummy()

def _safe_json(resp):
    try:
        return resp.json()
    except JSONDecodeError:
        return {"detail": f"HTTP {getattr(resp, 'status_code', '???')}"}

# =========================
# Auth
# =========================
@csrf_exempt
def auth_view(request):
    error = None
    if request.method == "GET":
        try:
            request.session.flush()
        except Exception:
            pass

    if request.method == "POST":
        action = request.POST.get("action")
        username = request.POST.get("username")
        password = request.POST.get("password")

        if action == "login":
            res = _post_json(
                TOKEN_URL, None,
                data={"username": username, "password": password},
                timeout=10
            )
            if getattr(res, "status_code", 400) == 200:
                request.session['api_token'] = _safe_json(res).get("token")
                return redirect("users_dashboard")
            error = "Неверный логин или пароль"

        elif action == "register":
            email = request.POST.get("email")
            first_name = request.POST.get("first_name", "")
            last_name = request.POST.get("last_name", "")

            res = _post_json(
                REGISTER_URL, None,
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                    "first_name": first_name,
                    "last_name": last_name
                },
                timeout=12
            )
            if getattr(res, "status_code", 400) in (200, 201):
                token = _safe_json(res).get("token")
                request.session['api_token'] = token
                return redirect("users_dashboard")
            try:
                error = _safe_json(res).get("detail", "Не удалось зарегистрироваться")
            except Exception:
                error = "Не удалось зарегистрироваться"

    return render(request, "dashboard/login.html", {"error": error})

# =========================
# Dashboard (bootstrap)
# =========================
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
    })

# =========================
# Logout
# =========================
@never_cache
def logout_view(request):
    request.session.pop('api_token', None)
    try:
        request.session.flush()
    except Exception:
        pass

    dj_logout(request)

    resp = redirect("auth")
    resp.delete_cookie(settings.SESSION_COOKIE_NAME)
    resp.delete_cookie("csrftoken")

    add_never_cache_headers(resp)
    return resp

# =========================
# Profile (bootstrap + параллель админ-хвостов)
# =========================
def profile_view(request):
    token = request.session.get("api_token")
    if not token:
        return redirect("auth")

    data = _get_json(BOOTSTRAP_URL, token, timeout=8)
    if not data:
        return redirect("logout")

    me        = data["me"]
    makes     = data["makes"]
    models    = data["models"]
    imgs      = data["car_images"]
    all_cars  = data["cars"]

    makes_map  = {m["id"]: m["name"] for m in makes}
    models_map = {m["id"]: {"name": m["name"], "make": m["make"]} for m in models}

    images_by_car = {}
    for img in imgs:
        images_by_car.setdefault(str(img.get("car")), []).append(img.get("image"))

    my_cars = [c for c in all_cars if c.get("seller") == me["id"]]
    default_img = request.build_absolute_uri(settings.MEDIA_URL + "car_images/default.png")

    for c in my_cars:
        c["make_name"]  = makes_map.get(c.get("make")) or "—"
        model_id = c.get("model")
        c["model_name"] = models_map.get(model_id, {}).get("name", "—")
        c["images"]     = images_by_car.get(str(c.get("VIN"))) or [default_img]
        c["status_ru"]  = status_ru(c.get("status"))
        try:
            price_int = int(float(c.get("price", 0)))
            c["price_fmt"] = intcomma(price_int).replace(",", " ")
        except Exception:
            c["price_fmt"] = c.get("price", "")

    role_map, my_roles = {}, set()
    urls = {
        "roles": ROLES_URL,
        "links": USER_ROLES_URL,
    }
    out = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(_get_json, u, token, 6): k for k, u in urls.items()}
        for f in as_completed(futs):
            out[futs[f]] = f.result() or []

    for r in out.get("roles", []):
        role_map[r.get("id")] = r.get("name")
    for link in out.get("links", []):
        if link.get("user") == me.get("id"):
            name = role_map.get(link.get("role"))
            if name:
                my_roles.add(name.lower())

    is_admin    = bool(me.get("is_superuser") or me.get("is_staff") or ('admin' in my_roles))
    is_analitic = ('analitic' in my_roles)

    if is_admin:
        admin_urls = {
            "users": f"{API_URL}users/",
            "roles": ROLES_URL,
            "logs":  f"{API_URL}admin/audit_logs/?limit=50&ordering=-action_time",
        }
        admin_out = {}
        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = {ex.submit(_get_json, u, token, 6): k for k, u in admin_urls.items()}
            for f in as_completed(futs):
                admin_out[futs[f]] = f.result() or []

        return render(request, "dashboard/admin.html", {
            "user": me,
            "users": admin_out.get("users", []),
            "roles": admin_out.get("roles", []),
            "audit_logs": admin_out.get("logs", []),
            "is_admin": True,
            "api_base": API_URL.rstrip("/"),
        })

    if is_analitic:
        return render(request, "dashboard/profile_analitic.html", {"user": me})

    headers = _h(token)
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            payload = {
                "username":   form.cleaned_data["username"],
                "first_name": form.cleaned_data["first_name"],
                "last_name":  form.cleaned_data["last_name"],
                "email":      form.cleaned_data["email"],
            }
            resp = SESSION.patch(ME_URL, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=10)
            if resp.status_code == 405:
                resp = SESSION.put(ME_URL, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=10)

            if resp.status_code in (200, 202):
                messages.success(request, "Профиль обновлён.")
                return redirect("profile")

            data_err = _safe_json(resp)
            attached = False
            if isinstance(data_err, dict):
                for field, errs in data_err.items():
                    msgs = errs if isinstance(errs, list) else [str(errs)]
                    if field in ("non_field_errors", "__all__"):
                        form.add_error(None, "; ".join(msgs)); attached = True
                    elif field in form.fields:
                        form.add_error(field, "; ".join(msgs)); attached = True
            if not attached:
                form.add_error(None, f"Ошибка {resp.status_code}: {getattr(resp, 'text', '')[:300]}")
    else:
        form = ProfileForm(initial={
            "username":   me.get("username", ""),
            "first_name": me.get("first_name", ""),
            "last_name":  me.get("last_name", ""),
            "email":      me.get("email", ""),
        })

    return render(request, "dashboard/profile_user.html", {
        "user": me,
        "form": form,
        "my_cars": my_cars,
        "default_img": default_img,
    })

@login_required
def profile_user(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлён.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "dashboard/profile_user.html", {"form": form})

# =========================
# Car detail (bootstrap + точечный GET)
# =========================
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
    resp = SESSION.get(f"{CARS_URL}{vin}/", headers=_h(token), timeout=6)
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

# =========================
# Actions
# =========================
def _auth_headers(request):
    token = request.session.get("api_token")
    return {"Authorization": f"Token {token}"} if token else {}

@login_required
def car_reserve(request, vin):
    """Кнопка «Зарезервировать» на карточке авто."""
    url  = f"{CARS_URL}{vin}/reserve/"
    resp = _post_json(url, request.session.get("api_token"), timeout=10)
    data = _safe_json(resp)
    if resp.status_code in (200, 201):
        messages.success(request, f"Заказ создан (#{data.get('id')}). Авто зарезервировано.")
    else:
        messages.error(request, data.get("detail") or "Не удалось зарезервировать авто.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

@login_required
def order_confirm(request, order_id):
    """Кнопка «Подтвердить заказ» в списке заказов."""
    url  = f"{ORDERS_URL}{order_id}/confirm/"
    resp = _post_json(url, request.session.get("api_token"), timeout=10)
    data = _safe_json(resp)
    if resp.status_code in (200, 201):
        messages.success(request, f"Транзакция создана (#{data.get('id')}). Заказ подтверждён.")
    else:
        messages.error(request, data.get("detail") or "Не удалось подтвердить заказ.")
    return redirect(request.META.get("HTTP_REFERER", "/orders/"))

@login_required
def order_seller_cancel(request, order_id):
    """Кнопка «Отменить как продавец» в списке заказов."""
    payload = {}
    reason = (request.POST.get("reason") or "").strip()
    if reason:
        payload["reason"] = reason

    url  = f"{ORDERS_URL}{order_id}/seller_cancel/"
    resp = _post_json(url, request.session.get("api_token"), json=payload, timeout=10)
    data = _safe_json(resp)
    if resp.status_code in (200, 204):
        messages.success(request, f"Заказ #{order_id} отменён.")
    else:
        messages.error(request, data.get("detail") or "Не удалось отменить заказ.")
    return redirect(request.META.get("HTTP_REFERER", "/orders/"))

@login_required
def make_bulk_reprice(request, make_id):
    """Форма «Пересчитать цены бренда» (для admin/superuser)."""
    if request.method == "POST":
        try:
            percent = float(request.POST.get("percent", ""))
        except ValueError:
            messages.error(request, "Процент должен быть числом (можно отрицательное).")
            return redirect(request.META.get("HTTP_REFERER", "/admin/makes/"))

        url  = f"{MAKES_URL}{make_id}/bulk_reprice/"
        resp = _post_json(url, request.session.get("api_token"), json={"percent": percent}, timeout=15)
        data = _safe_json(resp)
        if resp.status_code == 200:
            messages.success(request, f"Цены обновлены: затронуто {data.get('affected')} авто, {percent}%.")
        else:
            messages.error(request, data.get("detail") or "Не удалось пересчитать цены.")
        return redirect(request.META.get("HTTP_REFERER", "/admin/makes/"))

    return render(request, "dashboard/makes_bulk_reprice.html", {"make_id": make_id})

@login_required
def admin_panel(request):
    """
    Не трогаем ORM, всё берём из API.
    Сам экран админки рендерится в profile_view, здесь — пустой каркас
    (оставлено для совместимости роутинга).
    """
    token = request.session.get("api_token")
    is_admin = False
    me = _get_json(ME_URL, token) if token else None
    if me:
        roles = set((me.get("roles") or []))
        is_admin = bool(me.get("is_superuser") or me.get("is_staff") or ("admin" in roles))

    ctx = {
        "is_admin": is_admin,
        "has_token": bool(token),
        "users": [],
        "roles": [],
        "audit_logs": [],
        "makes": [],
    }
    return render(request, "dashboard/admin.html", ctx)