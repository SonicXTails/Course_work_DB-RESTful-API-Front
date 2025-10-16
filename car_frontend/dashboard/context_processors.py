# dashboard/context_processors.py
def role_flags(request):
    """
    Прокидываем в шаблоны флаг для простой проверки ролей из сессии.
    Логика максимально простая: если роль admin или anzalitic — считаем админ/аналитик.
    """
    roles = {str(r).lower() for r in request.session.get('roles', [])}
    is_admin_or_analitic = bool(
        ('admin' in roles) or ('analitic' in roles) or
        getattr(getattr(request, 'user', None), 'is_staff', False) or
        getattr(getattr(request, 'user', None), 'is_superuser', False)
    )
    return {
        'IS_ADMIN_OR_ANALITIC': is_admin_or_analitic,
        'IS_ADMIN_OR_ANALYST': is_admin_or_analitic,
    }

def theme(request):
    t = request.COOKIES.get('ui_theme') or request.session.get('ui_theme')
    if t not in ('dark', 'light'):
        t = 'dark'
    return {"THEME": t}
