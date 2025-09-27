import os
import requests
from requests.adapters import HTTPAdapter
from json import JSONDecodeError
from urllib.parse import urlencode

from django.conf import settings

# =========================
# API endpoints
# =========================
API_BASE = getattr(settings, "API_BASE_URL", os.getenv("API_BASE_URL", "http://localhost:8000"))
API_URL  = f"{API_BASE}/api/v1/"

REGISTER_URL   = f"{API_URL}auth/register/"
TOKEN_URL      = f"{API_BASE}/api-token-auth/"
ME_URL         = f"{API_URL}users/me/"
MAKES_URL      = f"{API_URL}makes/"
MODELS_URL     = f"{API_URL}models/"
CARS_URL       = f"{API_URL}cars/"
CAR_IMAGES_URL = f"{API_URL}car_images/"
USER_ROLES_URL = f"{API_URL}admin/user_roles/"
ROLES_URL      = f"{API_URL}admin/roles/"
ORDERS_URL     = f"{API_URL}orders/"
BOOTSTRAP_URL  = f"{API_URL}bootstrap/"

# =========================
# HTTP session (keep-alive)
# =========================
SESSION = requests.Session()
ADAPTER = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
SESSION.mount("http://", ADAPTER)
SESSION.mount("https://", ADAPTER)

# =========================
# Helpers
# =========================
STATUS_MAP_RU = {
    "available": "продаётся",
    "reserved": "зарезервировано",
    "sold": "продано",
    "unavailable": "недоступно",
}

def status_ru(val: str) -> str:
    return STATUS_MAP_RU.get((val or "").lower(), val or "—")

def _qs_without(original_get, *keys_to_remove, **replacements):
    params = original_get.copy()
    for k in keys_to_remove:
        params.pop(k, None)
    for k, v in replacements.items():
        if v in (None, '', []):
            params.pop(k, None)
        else:
            params[k] = v
    return urlencode(params, doseq=True)

def _h(token: str | None):
    return {"Authorization": f"Token {token}"} if token else {}

def _get_json(url: str, token: str | None, timeout=6):
    try:
        r = SESSION.get(url, headers=_h(token), timeout=timeout)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None

def _post_json(url: str, token: str | None, json=None, data=None, timeout=10):
    try:
        r = SESSION.post(url, headers=_h(token), json=json, data=data, timeout=timeout)
        return r
    except requests.RequestException:
        class _Dummy:
            status_code = 599
            def json(self): return {"detail": "network error"}
            text = "network error"
        return _Dummy()

def _safe_json(resp):
    try:
        return resp.json()
    except JSONDecodeError:
        return {"detail": f"HTTP {getattr(resp, 'status_code', '???')}"}
