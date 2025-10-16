from django.shortcuts import redirect

from .common import _get_json, ME_URL, ROLES_URL, USER_ROLES_URL

ADMIN_SYNONYMS = {"admin", "administrator", "админ", "администратор"}
ANALYTIC_SYNONYMS = {"analitic", "analyst", "аналитик"}

def _load_roles_into_session(request, token: str | None) -> set[str]:
    """Тянем /users/me/, кладём роли в сессию в нижнем регистре."""
    roles = set()
    if not token:
        request.session['roles'] = []
        request.session['is_admin'] = False
        request.session['is_analitic'] = False
        request.session['is_admin_or_analitic'] = False
        return roles

    me = _get_json(ME_URL, token, timeout=6) or {}
    for r in (me.get('roles') or []):
        try:
            roles.add(str(r).lower())
        except Exception:
            continue
    for r in (me.get('groups') or []):
        try:
            roles.add(str(r).lower())
        except Exception:
            continue

    if me.get("is_staff") or me.get("is_superuser"):
        roles.add("admin")

    is_admin    = bool(ADMIN_SYNONYMS    & roles)
    is_analitic = bool(ANALYTIC_SYNONYMS & roles)

    if not (is_admin or is_analitic):
        try:
            me_id = me.get("id")
            def _as_list(m):
                if isinstance(m, list): return m
                if isinstance(m, dict) and isinstance(m.get("results"), list): return m["results"]
                return []
            roles_payload = _get_json(ROLES_URL, token, timeout=6) or []
            links_payload = _get_json(USER_ROLES_URL, token, timeout=6) or []
            role_map = {}
            for r in _as_list(roles_payload):
                role_map[str(r.get("id"))] = str(r.get("name") or "").lower()
            for link in _as_list(links_payload):
                if link.get("user") == me_id:
                    name = role_map.get(str(link.get("role")))
                    if name:
                        roles.add(name)
            is_admin    = bool(ADMIN_SYNONYMS    & roles)
            is_analitic = bool(ANALYTIC_SYNONYMS & roles)
        except Exception:
            pass

    is_admin_or_analitic = is_admin or is_analitic



    is_admin_or_analitic = (is_admin or is_analitic)
    request.session["is_admin"] = is_admin

    request.session['roles'] = list(roles)
    request.session['is_admin'] = bool(is_admin)
    request.session['is_analitic'] = bool(is_analitic)
    request.session['is_admin_or_analitic'] = bool(is_admin_or_analitic)
    return roles

def _is_admin_or_analitic_session(request) -> bool:
    """Быстрая проверка по сессии; при отсутствии — подгружает из API."""
    val = request.session.get('is_admin_or_analitic')
    if val is not None:
        return bool(val)
    token = request.session.get('api_token')
    _load_roles_into_session(request, token)
    return bool(request.session.get('is_admin_or_analitic', False))

def _redirect_by_role(request):
    roles_raw = (
        request.session.get("roles")
        or request.session.get("user_roles")
        or request.session.get("groups")
        or []
    )

    try:
        roles = {str(r).lower() for r in roles_raw}
    except Exception:
        roles = {str(roles_raw).lower()} if roles_raw else set()

    is_admin_flag = bool(request.session.get("is_admin") or request.session.get("is_staff"))

    if is_admin_flag or any(r in roles for r in ("admin", "administrator", "админ", "администратор")):
        return redirect("admin_dashboard")

    if any(r in roles for r in ("analitic", "analyst", "аналитик")):
        return redirect("profile_analitic")

    return redirect("users_dashboard")

def is_admin(request) -> bool:
    val = request.session.get("is_admin")
    if val is None:
        token = request.session.get("api_token")
        _load_roles_into_session(request, token)
        val = request.session.get("is_admin", False)
    return bool(val)

def is_analitic(request) -> bool:
    """True, если пользователь – аналитик."""
    val = request.session.get("is_analitic")
    if val is None:
        token = request.session.get("api_token")
        _load_roles_into_session(request, token)
        val = request.session.get("is_analitic", False)
    return bool(val)