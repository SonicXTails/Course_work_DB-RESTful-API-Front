from django.urls import path
from .views.auth import auth_view, logout_view
from .views.dashboard import users_dashboard
from .views.profile import profile_view
from .views.cars import car_detail, car_reserve
from .views.orders import orders_view, order_confirm, order_seller_cancel, order_buyer_cancel
from .views.admin import admin_dashboard_view, make_bulk_reprice
from .views.analyst import analyst_profile_view

urlpatterns = [
    path('auth/', auth_view, name='auth'),
    path('logout/', logout_view, name='logout'),
    path('', users_dashboard, name='users_dashboard'),
    path('profile/', profile_view, name='profile'),
    path('cars/<str:vin>/', car_detail, name='car_detail'),
    path('cars/<str:vin>/reserve/', car_reserve, name='car_reserve'),
    path('orders/<int:order_id>/confirm/', order_confirm, name='order_confirm'),
    path('makes/<int:make_id>/bulk_reprice/', make_bulk_reprice, name='make_bulk_reprice'),
    path('orders/<int:order_id>/seller_cancel/', order_seller_cancel, name='order_seller_cancel'),
    path('orders/', orders_view, name='orders'),
    path('analyst/', analyst_profile_view, name='profile_analitic'),
    path('dashboard/admin/', admin_dashboard_view, name='admin_dashboard'),
    path("orders/<int:order_id>/buyer_cancel/", order_buyer_cancel, name="order_buyer_cancel"),
]
