import os, pytest, requests, random, string

skip_no_user = pytest.mark.skipif(
    not os.getenv("USER_TOKEN"),
    reason="USER_TOKEN не задан — пропускаем проверки прав для обычного пользователя."
)

@skip_no_user
def test_user_can_create_car_allowed(base_url, h_user, h_admin):
    # Берём валидные make/model из уже существующей записи, чтобы не упасть на валидации
    headers_read = h_user if "Authorization" in h_user else h_admin
    r_list = requests.get(f"{base_url}/api/v1/cars/", headers=headers_read, params={"ordering": "-price"})
    assert r_list.status_code == 200, r_list.text
    items = r_list.json() if isinstance(r_list.json(), list) else r_list.json().get("results", [])
    assert items, "Нет данных в /cars/ — не из чего взять make/model для валидного payload"
    sample = items[0]

    payload = {
        "VIN": "USER" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8)),
        "make": sample.get("make"),
        "model": sample.get("model"),
        "year": 2020,
        "price": 100000
    }

    r = requests.post(f"{base_url}/api/v1/cars/", headers=h_user, json=payload)
    # Ожидаем, что user может создать запись
    assert r.status_code in (201, 200), f"Ожидали разрешение (201/200) для user, но {r.status_code}: {r.text}"