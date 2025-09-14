from threading import local
_tls = local()

def set_current_user(user):
    _tls.user = user

def clear_current_user():
    _tls.user = None

def get_current_user():
    return getattr(_tls, "user", None)

class CurrentUserMiddleware:
    """Нужен, чтобы админка (session auth) тоже проставляла актёра."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, "user", None))
        try:
            return self.get_response(request)
        finally:
            clear_current_user()