from django.db.models.signals import pre_save, post_save, post_delete, post_migrate
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import Role, UserRole, AuditLog, Car, Order, Transaction, Review, CarImage, Make, Model
from django.contrib.auth import get_user_model
import datetime, decimal

User = get_user_model()
WATCHED_MODELS = [User, Role, UserRole, Car, Make, Model, CarImage, Order, Transaction, Review]

def make_json_safe(data: dict) -> dict:
    safe_data = {}
    for k, v in data.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            safe_data[k] = v.isoformat()
        elif isinstance(v, decimal.Decimal):
            safe_data[k] = float(v)
        else:
            safe_data[k] = v
    return safe_data

# --- Кешируем старые данные перед обновлением ---
@receiver(pre_save)
def cache_old_instance(sender, instance, **kwargs):
    if sender in WATCHED_MODELS and instance.pk:
        try:
            instance._old_data = make_json_safe(model_to_dict(sender.objects.get(pk=instance.pk)))
        except sender.DoesNotExist:
            instance._old_data = None

# --- CREATE и UPDATE ---
@receiver(post_save)
def log_create_update(sender, instance, created, **kwargs):
    if sender in WATCHED_MODELS:
        old_data = getattr(instance, "_old_data", None)
        new_data = make_json_safe(model_to_dict(instance))
        action = "CREATE" if created else "UPDATE"

        if action == "UPDATE" and old_data == new_data:
            return

        AuditLog.objects.create(
            user=None,
            action=action,
            table_name=sender.__name__,
            record_id=instance.pk,
            old_data=old_data,
            new_data=new_data
        )

# --- DELETE ---
@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender in WATCHED_MODELS:
        AuditLog.objects.create(
            user=None,
            action="DELETE",
            table_name=sender.__name__,
            record_id=instance.pk,
            old_data=make_json_safe(model_to_dict(instance)),
            new_data=None
        )

@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    default_roles = ['admin', 'analitic', 'user']
    for role_name in default_roles:
        Role.objects.get_or_create(name=role_name)

@receiver(post_save, sender=User)
def assign_admin_role(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        admin_role, _ = Role.objects.get_or_create(name='admin')
        UserRole.objects.get_or_create(user=instance, role=admin_role)