import requests
r = requests.post(
    "http://127.0.0.1:8000/api-token-auth/",
    data={"username":"123","password":"123"},
    headers={"Content-Type":"application/x-www-form-urlencoded"}
)
print(r.json())