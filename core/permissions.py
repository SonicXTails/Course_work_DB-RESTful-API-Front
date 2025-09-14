from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnlyAuthenticated(BasePermission):
    """
    Любой авторизованный может читать (GET/HEAD/OPTIONS).
    Любые изменения (POST/PUT/PATCH/DELETE) — только админ.
    """
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or ('admin' in getattr(user, 'roles', []))


class IsOwnerOrAdminForWrite(BasePermission):
    """
    Читать: авторизованные.
    Создавать/менять/удалять: владелец объекта ИЛИ админ.

    Владелец определяется по первому совпавшему полю из:
    seller / buyer / author / user (чтобы работало для Car/Order/Review/UserRole).
    """
    OWNER_ATTRS = ('seller', 'buyer', 'author', 'user')

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if view.action in ('list', 'retrieve', 'create'):
            return True
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return True
        if user.is_superuser or ('admin' in getattr(user, 'roles', [])):
            return True
        for attr in self.OWNER_ATTRS:
            owner = getattr(obj, attr, None)
            owner_id = getattr(owner, 'id', owner)
            if owner_id == user.id:
                return True
        return False
