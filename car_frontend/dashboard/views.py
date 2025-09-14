import requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime

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

    res_user = requests.get(ME_URL, headers=headers)
    if res_user.status_code != 200:
        return redirect("logout")
    user_data = res_user.json()

    roles = []
    role_id_to_name = {}
    res_roles_list = requests.get(f"{API_URL}admin/roles/", headers=headers)
    if res_roles_list.status_code == 200:
        roles = res_roles_list.json()
        role_id_to_name = {r["id"]: r["name"] for r in roles}

    res_user_roles = requests.get(f"{API_URL}admin/user_roles/", headers=headers)
    user_role_name = None
    if res_user_roles.status_code == 200:
        for link in res_user_roles.json():
            if link.get("user") == user_data.get("id"):
                rid = link.get("role")
                name = role_id_to_name.get(rid)
                if name:
                    if name == "admin":
                        user_role_name = "admin"
                        break
                    if not user_role_name:
                        user_role_name = name

    audit_logs = []
    res_logs = requests.get(f"{API_URL}admin/audit_logs/?limit=20&ordering=-action_time", headers=headers)
    if res_logs.status_code == 200:
        raw_logs = res_logs.json()
        for log in raw_logs:
            dt = parse_datetime(log.get("action_time"))
            if dt:
                log["action_time"] = localtime(dt)
            audit_logs.append(log)

    users = []
    res_users = requests.get(f"{API_URL}users/", headers=headers)
    if res_users.status_code == 200:
        users = res_users.json()

    if user_role_name == "admin":
        template = "dashboard/profile_admin.html"
        context = {
            "user": user_data,
            "audit_logs": audit_logs,
            "users": users,
            "roles": roles,
        }
    elif user_role_name == "analitic":
        template = "dashboard/profile_analitic.html"
        context = {"user": user_data}
    else:
        template = "dashboard/profile_user.html"
        context = {"user": user_data}

    return render(request, template, context)