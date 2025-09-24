import os, pytest, requests

@pytest.mark.parametrize("payload", [
    {"q": "' OR '1'='1"},
    {"make": "Toyota'; DROP TABLE cars;--"},
    {"ordering": "price;DROP TABLE cars;--"}
])
def test_filters_resist_sqli(base_url, h_user, h_admin, payload):
    # Если USER_TOKEN нет, используем админский токен для read-only проверки
    headers = h_user if 'Authorization' in h_user else h_admin
    r = requests.get(f"{base_url}/api/v1/cars/", headers=headers, params=payload)
    # Должно быть безопасно: 200 (экранировано) или 400/422 (валидатор). 500 и 401 недопустимы.
    assert r.status_code in (200,400,422), r.text
