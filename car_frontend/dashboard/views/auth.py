from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth import logout as dj_logout
from django.utils.cache import add_never_cache_headers
from django.conf import settings
from django.shortcuts import redirect
from .theme_api import load_theme_from_api

from .common import TOKEN_URL, REGISTER_URL, _post_json, _safe_json
from .roles import _load_roles_into_session, _redirect_by_role

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
                token = _safe_json(res).get("token")
                request.session["api_token"] = token
                _load_roles_into_session(request, token)
                load_theme_from_api(request, token)
                return _redirect_by_role(request)

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
                request.session["api_token"] = token
                _load_roles_into_session(request, token)
                return _redirect_by_role(request)

            try:
                error = _safe_json(res).get("detail", "Не удалось зарегистрироваться")
            except Exception:
                error = "Не удалось зарегистрироваться"

    return render(request, "dashboard/login.html", {"error": error})

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
