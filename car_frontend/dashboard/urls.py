from django.urls import path
from . import views

urlpatterns = [
    path('auth/', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.users_dashboard, name='users_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('cars/<str:vin>/', views.car_detail, name='car_detail'),
    path("cars/<str:vin>/reserve/", views.car_reserve, name="car_reserve"),
    path("orders/<int:order_id>/confirm/", views.order_confirm, name="order_confirm"),
    path("makes/<int:make_id>/bulk_reprice/", views.make_bulk_reprice, name="make_bulk_reprice"),
    path("orders/<int:order_id>/seller_cancel/", views.order_seller_cancel,  name="order_seller_cancel"),
]