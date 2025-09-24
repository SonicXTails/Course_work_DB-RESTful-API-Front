
import json, random, string, pytest, requests

def test_cars_crud_flow(base_url, h_admin, h_user):
    payload = {
        "model_id": 1,
        "price": 123456,
        "year": 2022,
        "vin": "TEST" + "".join(random.choices(string.ascii_uppercase+string.digits, k=8))
    }
    r = requests.post(f"{base_url}/api/v1/cars/", headers=h_admin, json=payload)
    assert r.status_code in (201, 400), r.text
    if r.status_code == 201:
        car = r.json()
        car_id = car.get("id")
        r = requests.get(f"{base_url}/api/v1/cars/{car_id}/", headers=h_user)
        assert r.status_code == 200, r.text
        r = requests.patch(f"{base_url}/api/v1/cars/{car_id}/", headers=h_admin, json={"price": 999999})
        assert r.status_code in (200, 202), r.text
        r = requests.delete(f"{base_url}/api/v1/cars/{car_id}/", headers=h_admin)
        assert r.status_code in (204, 200), r.text