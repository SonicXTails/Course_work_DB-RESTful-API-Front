
import pytest, requests, random, string

def test_audit_created_on_update(base_url, h_admin):
    vin = "AUD" + "".join(random.choices(string.ascii_uppercase+string.digits, k=8))
    payload = {"model_id": 1, "price": 111111, "year": 2021, "vin": vin}
    r = requests.post(f"{base_url}/api/v1/cars/", headers=h_admin, json=payload)
    if r.status_code == 201:
        car_id = r.json()["id"]
        requests.patch(f"{base_url}/api/v1/cars/{car_id}/", headers=h_admin, json={"price": 222222})
        q = requests.get(f"{base_url}/api/v1/audit-logs/", headers=h_admin, params={"entity":"car","entity_id":car_id})
        assert q.status_code == 200, q.text
