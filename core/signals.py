from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Role, UserRole

User = get_user_model()

@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    # 1. Создаём стандартные роли
    default_roles = ['admin', 'analitic', 'user']
    for role_name in default_roles:
        Role.objects.get_or_create(name=role_name)

    # 2. Назначаем роль 'admin' первому суперпользователю
    admin_role = Role.objects.get(name='admin')
    superusers = User.objects.filter(is_superuser=True)
    for user in superusers:
        # проверяем, есть ли уже назначенная роль 'admin'
        if not user.userrole_set.filter(role=admin_role).exists():
            UserRole.objects.create(user=user, role=admin_role)
