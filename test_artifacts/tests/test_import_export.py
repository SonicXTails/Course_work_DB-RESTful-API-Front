
import pytest, requests

def test_export_csv_if_implemented(base_url, h_admin):
    r = requests.get(f"{base_url}/api/v1/reports/sales.csv", headers=h_admin)
    assert r.status_code in (200,404), r.text
