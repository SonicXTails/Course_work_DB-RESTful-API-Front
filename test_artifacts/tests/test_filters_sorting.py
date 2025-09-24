import os, pytest, requests

def test_cars_filters_and_sort(base_url, h_user, h_admin):
    # Если USER_TOKEN не задан -> читаем админом (только для read-only тестов)
    headers = h_user if 'Authorization' in h_user else h_admin

    params = {"make": "Toyota", "price__lte": 500000}
    r = requests.get(f"{base_url}/api/v1/cars/", headers=headers, params=params)
    assert r.status_code == 200, r.text

    params = {"ordering": "-price"}
    r = requests.get(f"{base_url}/api/v1/cars/", headers=headers, params=params)
    assert r.status_code == 200, r.text
