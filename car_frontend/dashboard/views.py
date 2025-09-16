import requests
from django.contrib.humanize.templatetags.humanize import intcomma
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime
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

@csrf_exempt
def auth_view(request):
    error = None

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


def users_dashboard(request):
    token = request.session.get("api_token")
    headers = {"Authorization": f"Token {token}"} if token else {}

    user_data = None
    cars = []
    makes_map = {}
    models_map = {}
    images_by_car = {}

    if token:
        r_user = requests.get(ME_URL, headers=headers)
        if r_user.status_code == 200:
            user_data = r_user.json()

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
            r_cars = requests.get(CARS_URL, headers=headers, timeout=5)
            if r_cars.ok:
                cars = r_cars.json()
        except Exception:
            cars = []

        try:
            r_imgs = requests.get(CAR_IMAGES_URL, headers=headers, timeout=5)
            if r_imgs.ok:
                for img in r_imgs.json():
                    car_pk = img.get("car")
                    images_by_car.setdefault(car_pk, []).append(img.get("image"))
        except Exception:
            pass

        for c in cars:
                    c["make_name"]  = makes_map.get(c.get("make")) or "—"
                    model_id = c.get("model")
                    c["model_name"] = models_map.get(model_id, {}).get("name", "—")
                    c["images"]     = images_by_car.get(c.get("VIN")) or []
                    c["status_ru"]  = status_ru(c.get("status"))

                    dt = parse_datetime(c.get("created_at") or "")
                    if dt:
                        c["created_at_fmt"] = localtime(dt).strftime("%d.%m.%Y %H:%M")
                    else:
                        c["created_at_fmt"] = "—"

                    try:
                        price_dec = Decimal(str(c.get("price", "0")))
                        price_int = int(price_dec)
                        c["price_fmt"] = f"{price_int:,}".replace(",", " ")
                    except Exception:
                        c["price_fmt"] = str(c.get("price", "0"))

    return render(request, "dashboard/index.html", {
        "user": user_data,
        "cars": cars,
    })

def logout_view(request):
    request.session.flush()
    return redirect("auth")


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