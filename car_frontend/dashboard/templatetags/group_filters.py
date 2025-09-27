from django import template
register = template.Library()

@register.filter
def has_group(user, group_name):
    try:
        return user.is_authenticated and user.groups.filter(name__iexact=group_name).exists()
    except Exception:
        return False