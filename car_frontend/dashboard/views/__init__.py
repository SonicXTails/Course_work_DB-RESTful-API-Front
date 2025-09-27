# Реэкспорт, чтобы существующие импорты из ". import views" продолжали работать.
from .auth import auth_view, logout_view
from .dashboard import users_dashboard
from .profile import profile_view
from .cars import car_detail, car_reserve
from .orders import orders_view, order_confirm, order_seller_cancel
from .admin import admin_dashboard_view, make_bulk_reprice
from .analyst import analyst_profile_view

__all__ = [
    "auth_view", "logout_view",
    "users_dashboard", "profile_view",
    "car_detail", "car_reserve",
    "orders_view", "order_confirm", "order_seller_cancel",
    "admin_dashboard_view", "make_bulk_reprice",
    "analyst_profile_view",
]
