import requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

API_URL = "http://localhost:8000/api/v1/"
TOKEN_URL = "http://localhost:8000/api-token-auth/"

@csrf_exempt
def login_view(request):
    if request.method == "POST":
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
            return render(request, "dashboard/login.html", {"error": "Неверный логин или пароль"})

    return render(request, "dashboard/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def users_dashboard(request):
    token = request.session.get('api_token')
    if not token:
        return redirect("login")

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
        return redirect("login")

    headers = {"Authorization": f"Token {token}"}
    res = requests.get(f"{API_URL}audit_logs/", headers=headers)
    logs = res.json() if res.status_code == 200 else []
    return render(request, "dashboard/audit_dashboard.html", {"logs": logs})