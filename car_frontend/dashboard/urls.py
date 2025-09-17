from django.urls import path
from . import views

urlpatterns = [
    path('auth/', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.users_dashboard, name='users_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('cars/<str:vin>/', views.car_detail, name='car_detail'),
]