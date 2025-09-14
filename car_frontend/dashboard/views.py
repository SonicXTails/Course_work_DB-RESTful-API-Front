import requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime
from json import JSONDecodeError

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ProfileForm

API_URL = "http://localhost:8000/api/v1/"
REGISTER_URL = f"{API_URL}auth/register/"
TOKEN_URL = "http://localhost:8000/api-token-auth/"
ME_URL = f"{API_URL}users/me/"

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
                error = res.json().get("detail", "Не удалось зарегистрироваться")

    return render(request, "dashboard/login.html", {"error": error})


def users_dashboard(request):
    token = request.session.get("api_token")
    user_data = None

    if token:
        headers = {"Authorization": f"Token {token}"}
        res = requests.get(ME_URL, headers=headers)
        if res.status_code == 200:
            user_data = res.json()

    return render(request, "dashboard/index.html", {"user": user_data})


def logout_view(request):
    request.session.flush()
    return redirect("auth")


def profile_view(request):
    token = request.session.get("api_token")
    if not token:
        return redirect("auth")
    headers = {"Authorization": f"Token {token}"}

    # 1) Текущий пользователь (теперь в ответе есть is_staff/is_superuser)
    res_user = requests.get(ME_URL, headers=headers)
    if res_user.status_code != 200:
        return redirect("logout")
    me = res_user.json()

    # 2) Определяем роль
    is_admin = bool(me.get("is_superuser") or me.get("is_staff"))
    is_analitic = False
    if not is_admin:
        # тянем свои user_roles (вьюсет уже ограничивает чужие записи)
        try:
            res_links = requests.get(USER_ROLES_URL, headers=headers, timeout=5)
            links = res_links.json() if res_links.status_code == 200 else []
        except Exception:
            links = []

        # подтянем список ролей, чтобы сопоставить id -> name
        role_map = {}
        try:
            res_roles = requests.get(ROLES_URL, headers=headers, timeout=5)
            if res_roles.status_code == 200:
                for r in res_roles.json():
                    role_map[r.get("id")] = r.get("name")
        except Exception:
            pass

        # соберём имена ролей текущего юзера
        my_roles = {role_map.get(link.get("role")) for link in links if link.get("user") == me.get("id")}
        my_roles = {r for r in my_roles if r}
        is_analitic = ("analitic" in {r.lower() for r in my_roles})

    # 3) Ветвление шаблонов
    if is_admin:
        # тут твой контекст админа: audit_logs, users, roles и т.д.
        return render(request, "dashboard/profile_admin.html", {
            "user": me,
            # "audit_logs": ...,
            # "users": ...,
            # "roles": ...,
        })

    if is_analitic:
        return render(request, "dashboard/profile_analitic.html", {"user": me})

    # === Обычный пользователь: форма + PATCH/PUT на /users/me/ ===
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

            # Красиво прикрепим ошибки API к форме
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

    return render(request, "dashboard/profile_user.html", {"user": me, "form": form})


@login_required
def profile_user(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлён.")
            return redirect("profile")  # имя роута см. ниже
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "dashboard/profile_user.html", {"form": form})