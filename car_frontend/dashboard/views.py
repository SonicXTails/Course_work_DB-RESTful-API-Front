import requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

API_URL = "http://localhost:8000/api/v1/"
REGISTER_URL = f"{API_URL}register/"
TOKEN_URL = "http://localhost:8000/api-token-auth/"

@csrf_exempt
def auth_view(request):
    error = None

    if request.method == "POST":
        action = request.POST.get("action")  # "login" или "register"

        if action == "login":
            username = request.POST.get("username")
            password = request.POST.get("password")

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
            username = request.POST.get("username")
            email = request.POST.get("email")
            password = request.POST.get("password")
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
                # логин после регистрации
                login_res = requests.post(
                    TOKEN_URL,
                    data={"username": username, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if login_res.status_code == 200:
                    request.session['api_token'] = login_res.json().get("token")
                    return redirect("users_dashboard")
                else:
                    error = "Ошибка авторизации после регистрации"
            else:
                error = res.json().get("detail", "Не удалось зарегистрироваться")

    return render(request, "dashboard/login.html", {"error": error})

def logout_view(request):
    request.session.flush()
    return redirect("auth")


def users_dashboard(request):
    token = request.session.get('api_token')
    if not token:
        return redirect("auth")

    headers = {"Authorization": f"Token {token}"}

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        payload = {
            "username": request.POST.get("username"),
            "email": request.POST.get("email")
        }
        if "edit_user" in request.POST:
            requests.put(f"{API_URL}users/{user_id}/", headers=headers, json=payload)
        if "delete_user" in request.POST:
            requests.delete(f"{API_URL}users/{user_id}/", headers=headers)
        return redirect("users_dashboard")

    res = requests.get(f"{API_URL}users/", headers=headers)
    users = res.json() if res.status_code == 200 else []
    return render(request, "dashboard/users_dashboard.html", {"users": users})


def audit_dashboard(request):
    token = request.session.get('api_token')
    if not token:
        return redirect("auth")

    headers = {"Authorization": f"Token {token}"}
    res = requests.get(f"{API_URL}audit_logs/", headers=headers)
    logs = res.json() if res.status_code == 200 else []
    return render(request, "dashboard/audit_dashboard.html", {"logs": logs})