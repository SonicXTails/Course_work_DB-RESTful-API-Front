from rest_framework.permissions import BasePermission, SAFE_METHODS

__all__ = [
    "IsAdminOrReadOnlyAuthenticated",
    "IsOwnerOrAdminForWrite",
    "IsAdmin",
    "IsAnalyst",
]

def _has_role(user, *names):
    try:
        roles = set(getattr(user, "roles", []))
    except Exception:
        roles = set()
    return bool(roles & set(names))

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and (_has_role(u, "admin") or getattr(u, "is_superuser", False)))

class IsAnalyst(BasePermission):
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and (_has_role(u, "analitic", "admin") or getattr(u, "is_superuser", False)))

class IsAdminOrReadOnlyAuthenticated(BasePermission):
    """
    Читать (GET/HEAD/OPTIONS) — любой авторизованный.
    Писать (POST/PUT/PATCH/DELETE) — только админ/суперпользователь.
    """
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        if not u or not u.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _has_role(u, "admin") or getattr(u, "is_superuser", False)

class IsOwnerOrAdminForWrite(BasePermission):
    """
    Читать — авторизованные.
    Писать/удалять — владелец объекта или админ.
    Владелец определяется по полям seller / buyer / author / user (первое совпавшее).
    """
    OWNER_ATTRS = ("seller", "buyer", "author", "user")

    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        if getattr(u, "is_superuser", False) or _has_role(u, "admin"):
            return True
        for attr in self.OWNER_ATTRS:
            owner = getattr(obj, attr, None)
            owner_id = getattr(owner, "id", owner)
            if owner_id == u.id:
                return True
        return False