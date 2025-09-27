from concurrent.futures import ThreadPoolExecutor, as_completed
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.humanize.templatetags.humanize import intcomma

from django.conf import settings

from .common import (
    API_URL, BOOTSTRAP_URL, ROLES_URL, USER_ROLES_URL, ME_URL,
    _get_json, _post_json, _safe_json, _h, status_ru
)
from ..forms import ProfileForm

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
    urls = {"roles": ROLES_URL, "links": USER_ROLES_URL}
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
            resp = _post_json(ME_URL, token, json=payload, timeout=10)
            if getattr(resp, "status_code", 400) == 405:
                resp = _post_json(ME_URL, token, json=payload, timeout=10)

            if getattr(resp, "status_code", 400) in (200, 202):
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
                form.add_error(None, f"Ошибка {getattr(resp, 'status_code', '???')}: {getattr(resp, 'text', '')[:300]}")
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
