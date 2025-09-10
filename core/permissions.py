from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        # если не авторизован — отказ
        if not request.user.is_authenticated:
            return False
        # суперпользователь всегда имеет доступ
        if request.user.is_superuser:
            return True
        return 'Администратор' in request.user.roles