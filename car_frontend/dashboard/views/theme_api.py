from .common import _get_json, API_URL

def load_theme_from_api(request, token: str | None) -> str:
    theme = "dark"
    if not token:
        request.session["theme"] = theme
        return theme
    # пробуем отдельную точку
    data = _get_json(f"{API_URL}users/me/theme/", token, timeout=6) or {}
    t = (data.get("theme") or "").lower() if isinstance(data, dict) else ""
    if t in ("dark", "light"):
        theme = t
    request.session["theme"] = theme
    return theme