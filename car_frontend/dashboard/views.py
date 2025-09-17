import requests
from urllib.parse import urlencode
from django.contrib.humanize.templatetags.humanize import intcomma
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime
from django.conf import settings
from django.contrib.auth import logout as dj_logout
from django.views.decorators.cache import never_cache
from django.utils.cache import add_never_cache_headers
from django.shortcuts import redirect
from decimal import Decimal
from json import JSONDecodeError

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm

API_URL = "http://localhost:8000/api/v1/"
REGISTER_URL = f"{API_URL}auth/register/"
TOKEN_URL = "http://localhost:8000/api-token-auth/"
ME_URL = f"{API_URL}users/me/"
MAKES_URL = f"{API_URL}makes/"
MODELS_URL = f"{API_URL}models/"
CARS_URL = f"{API_URL}cars/"
CAR_IMAGES_URL = f"{API_URL}car_images/"
USER_ROLES_URL = f"{API_URL}admin/user_roles/"
ROLES_URL = f"{API_URL}admin/roles/"

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
            res = requests.post(
                TOKEN_URL,
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if res.status_code == 200:
                request.session['api_token'] = res.json().get("token")
                return redirect("users_dashboard")
            else:
                error = "Неверный логин или пароль"

        elif action == "register":
            email = request.POST.get("email")
            first_name = request.POST.get("first_name", "")
            last_name = request.POST.get("last_name", "")

            res = requests.post(
                REGISTER_URL,
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                    "first_name": first_name,
                    "last_name": last_name
                },
                headers={"Content-Type": "application/json"}
            )

            if res.status_code in [200, 201]:
                token = res.json().get("token")
                request.session['api_token'] = token
                return redirect("users_dashboard")
            else:
                try:
                    error = res.json().get("detail", "Не удалось зарегистрироваться")
                except JSONDecodeError:
                    error = "Не удалось зарегистрироваться"
                    
    return render(request, "dashboard/login.html", {"error": error})


from urllib.parse import urlencode
from decimal import Decimal
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime

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

def users_dashboard(request):
    token = request.session.get("api_token")
    headers = {"Authorization": f"Token {token}"} if token else {}

    user_data = None
    cars = []
    makes_map, models_map = {}, {}
    images_by_car = {}

    # --- профиль ---
    if token:
        try:
            r_user = requests.get(ME_URL, headers=headers, timeout=5)
            if r_user.ok:
                user_data = r_user.json()
        except Exception:
            user_data = None

    # --- справочники ---
    try:
        r_makes = requests.get(MAKES_URL, headers=headers, timeout=5)
        if r_makes.ok:
            for m in r_makes.json():
                makes_map[m["id"]] = m["name"]
    except Exception:
        pass
    try:
        r_models = requests.get(MODELS_URL, headers=headers, timeout=5)
        if r_models.ok:
            for m in r_models.json():
                models_map[m["id"]] = {"name": m["name"], "make": m["make"]}
    except Exception:
        pass

    # --- загрузка машин без фильтра ---
    try:
        r_cars = requests.get(CARS_URL, headers=headers, timeout=5)
        if r_cars.ok:
            cars = r_cars.json()
    except Exception:
        cars = []

    # --- фотки одним махом ---
    try:
        r_imgs = requests.get(CAR_IMAGES_URL, headers=headers, timeout=5)
        if r_imgs.ok:
            for img in r_imgs.json():
                car_pk = img.get("car")
                images_by_car.setdefault(str(car_pk), []).append(img.get("image"))
    except Exception:
        pass

    # --- нормализация и подготовка служебных полей ---
    for c in cars:
        c["make_name"]  = makes_map.get(c.get("make")) or "—"
        model_id = c.get("model")
        c["model_name"] = models_map.get(model_id, {}).get("name", "—")

        # изображения: пробуем VIN и id
        imgs = images_by_car.get(str(c.get("VIN"))) or images_by_car.get(str(c.get("id"))) or []
        c["images"] = imgs

        # продавец
        first = c.get("seller_first_name") or ""
        last  = c.get("seller_last_name") or ""
        c["seller_full_name"] = (f"{first} {last}".strip() or str(c.get("seller") or "—"))

        # статус
        c["status_ru"] = status_ru(c.get("status"))

        # даты/цены/год
        dt = parse_datetime(c.get("created_at") or "")
        c["_created_dt"] = localtime(dt) if dt else None
        c["created_at_fmt"] = c["_created_dt"].strftime("%d.%m.%Y %H:%M") if c["_created_dt"] else "—"

        try:
            c["_price_int"] = int(Decimal(str(c.get("price") or 0)))
        except Exception:
            c["_price_int"] = None
        c["price_fmt"] = f"{c['_price_int']:,}".replace(",", " ") if c["_price_int"] is not None else str(c.get("price","0"))

        try:
            c["_year_int"] = int(c.get("year")) if c.get("year") is not None else None
        except Exception:
            c["_year_int"] = None

    # --- ЛОКАЛЬНЫЕ ФИЛЬТРЫ ---
    g = request.GET
    q          = (g.get('q') or '').strip().lower()
    status     = (g.get('status') or '').strip().lower()
    year_min   = g.get('year_min')
    year_max   = g.get('year_max')
    price_min  = g.get('price_min')
    price_max  = g.get('price_max')
    sort       = g.get('sort')

    def _passes(c):
        # поиск по make/model/VIN
        if q:
            hay = " ".join([
                str(c.get("make_name") or ""),
                str(c.get("model_name") or ""),
                str(c.get("VIN") or ""),
            ]).lower()
            if q not in hay:
                return False
        # статус
        if status and (str(c.get("status") or "").lower() != status):
            return False
        # год
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
        # цена
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

    # --- ЛОКАЛЬНАЯ СОРТИРОВКА ---
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

    # --- пагинация и QS для шаблона ---
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

@never_cache
def logout_view(request):
    # 1) Убираем всё из сессии
    request.session.pop('api_token', None)
    try:
        request.session.flush()           # удалит сессию и создаст новую пустую
    except Exception:
        pass

    # 2) Разлогиниваем Django-пользователя (если он есть)
    dj_logout(request)

    # 3) На всякий случай удалим куки сессии и CSRF у ответа
    resp = redirect("auth")
    resp.delete_cookie(settings.SESSION_COOKIE_NAME)
    resp.delete_cookie("csrftoken")

    # 4) Запретим кэш
    add_never_cache_headers(resp)
    return resp


def profile_view(request):
    token = request.session.get("api_token")
    if not token:
        return redirect("auth")
    headers = {"Authorization": f"Token {token}"}

    res_user = requests.get(ME_URL, headers=headers)
    if res_user.status_code != 200:
        return redirect("logout")
    me = res_user.json()

    my_cars, makes_map, models_map, images_by_car = [], {}, {}, {}

    try:
        r_makes = requests.get(MAKES_URL, headers=headers, timeout=5)
        if r_makes.ok:
            for m in r_makes.json():
                makes_map[m["id"]] = m["name"]
    except Exception:
        pass
    try:
        r_models = requests.get(MODELS_URL, headers=headers, timeout=5)
        if r_models.ok:
            for m in r_models.json():
                models_map[m["id"]] = {"name": m["name"], "make": m["make"]}
    except Exception:
        pass

    try:
        url = f"{CARS_URL}?seller={me['id']}"
        r_cars = requests.get(url, headers=headers, timeout=5)
        if r_cars.ok:
            my_cars = r_cars.json()
            if isinstance(my_cars, list):
                my_cars = [c for c in my_cars if c.get("seller") == me["id"]]
    except Exception:
        my_cars = []

    try:
        r_imgs = requests.get(CAR_IMAGES_URL, headers=headers, timeout=5)
        if r_imgs.ok:
            for img in r_imgs.json():
                car_pk = img.get("car")
                images_by_car.setdefault(car_pk, []).append(img.get("image"))
    except Exception:
        pass

    default_img = request.build_absolute_uri(settings.MEDIA_URL + "car_images/default.png")
    for c in my_cars:
        c["make_name"]  = makes_map.get(c.get("make")) or "—"
        model_id = c.get("model")
        c["model_name"] = models_map.get(model_id, {}).get("name", "—")
        imgs = images_by_car.get(c.get("VIN")) or []
        c["images"] = imgs if imgs else [default_img]
        c["status_ru"] = status_ru(c.get("status"))

        try:
            price_int = int(float(c.get("price", 0)))
            c["price_fmt"] = intcomma(price_int).replace(",", " ")
        except Exception:
            c["price_fmt"] = c.get("price", "")

    role_map = {}
    my_roles = set()
    try:
        res_roles = requests.get(ROLES_URL, headers=headers, timeout=5)
        if res_roles.ok:
            for r in res_roles.json():
                role_map[r["id"]] = r["name"]
        res_links = requests.get(USER_ROLES_URL, headers=headers, timeout=5)
        if res_links.ok:
            for link in res_links.json():
                if link.get("user") == me.get("id"):
                    name = role_map.get(link.get("role"))
                    if name:
                        my_roles.add(name.lower())
    except Exception:
        pass

    is_admin = bool(me.get("is_superuser") or me.get("is_staff") or ('admin' in my_roles))
    is_analitic = ('analitic' in my_roles)

    if is_admin:
        users, roles, audit_logs = [], [], []
        try:
            r_users = requests.get(f"{API_URL}users/", headers=headers, timeout=5)
            if r_users.ok:
                users = r_users.json()
        except Exception:
            pass
        try:
            r_roles = requests.get(ROLES_URL, headers=headers, timeout=5)
            if r_roles.ok:
                roles = r_roles.json()
        except Exception:
            pass
        try:
            r_logs = requests.get(f"{API_URL}admin/audit_logs/?limit=50&ordering=-action_time",
                                  headers=headers, timeout=5)
            if r_logs.ok:
                audit_logs = r_logs.json()
        except Exception:
            pass

        return render(request, "dashboard/admin.html", {
            "user": me,
            "users": users,
            "roles": roles,
            "audit_logs": audit_logs,
        })

    if is_analitic:
        return render(request, "dashboard/profile_analitic.html", {"user": me})

    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            payload = {
                "username":   form.cleaned_data["username"],
                "first_name": form.cleaned_data["first_name"],
                "last_name":  form.cleaned_data["last_name"],
                "email":      form.cleaned_data["email"],
            }
            resp = requests.patch(ME_URL, headers={**headers, "Content-Type": "application/json"}, json=payload)
            if resp.status_code == 405:
                resp = requests.put(ME_URL, headers={**headers, "Content-Type": "application/json"}, json=payload)

            if resp.status_code in (200, 202):
                messages.success(request, "Профиль обновлён.")
                return redirect("profile")

            try:
                data = resp.json()
            except JSONDecodeError:
                data = {"__all__": [resp.text[:300] or "Не удалось сохранить изменения"]}

            attached = False
            if isinstance(data, dict):
                for field, errs in data.items():
                    msgs = errs if isinstance(errs, list) else [str(errs)]
                    if field in ("non_field_errors", "__all__"):
                        form.add_error(None, "; ".join(msgs)); attached = True
                    elif field in form.fields:
                        form.add_error(field, "; ".join(msgs)); attached = True
            if not attached:
                form.add_error(None, f"Ошибка {resp.status_code}: {resp.text[:300]}")
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


def car_detail(request, vin):
    token = request.session.get("api_token")
    headers = {"Authorization": f"Token {token}"} if token else {}
    makes_map, models_map, images_by_car = {}, {}, {}
    car, not_found = None, False
    me = None
    if token:
        try:
            r_user = requests.get(ME_URL, headers=headers, timeout=5)
            if r_user.ok:
                me = r_user.json()
        except Exception:
            me = None

    try:
        r_makes = requests.get(MAKES_URL, headers=headers, timeout=5)
        if r_makes.ok:
            for m in r_makes.json():
                makes_map[m["id"]] = m["name"]
    except Exception:
        pass
    try:
        r_models = requests.get(MODELS_URL, headers=headers, timeout=5)
        if r_models.ok:
            for m in r_models.json():
                models_map[m["id"]] = {"name": m["name"], "make": m["make"]}
    except Exception:
        pass
    try:
        r_imgs = requests.get(CAR_IMAGES_URL, headers=headers, timeout=5)
        if r_imgs.ok:
            for img in r_imgs.json():
                images_by_car.setdefault(img.get("car"), []).append(img.get("image"))
    except Exception:
        pass

    try:
        r = requests.get(f"{CARS_URL}{vin}/", headers=headers, timeout=5)
        if r.ok:
            car = r.json()
        else:
            not_found = True
    except Exception:
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
        car["images"]     = images_by_car.get(car.get("VIN")) or []

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
        if seller_id:
            try:
                r_reviews = requests.get(f"{API_URL}reviews/", headers=headers, timeout=5)
                if r_reviews.ok:
                    all_reviews = r_reviews.json()
                    seller_reviews = [rv for rv in all_reviews if rv.get("target") == seller_id]

                    ratings = [int(rv.get("rating", 0)) for rv in seller_reviews if rv.get("rating") is not None]
                    if ratings:
                        seller_rating_count = len(ratings)
                        seller_rating_avg = round(sum(ratings) / seller_rating_count, 1)

                    if me:
                        my_already_reviewed = any((rv.get("author") == me.get("id")) for rv in seller_reviews)
            except Exception:
                pass

        if me and seller_id and me.get("id") != seller_id and not my_already_reviewed:
            can_review = True

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