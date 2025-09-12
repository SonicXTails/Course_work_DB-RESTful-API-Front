from django.urls import path
from . import views

urlpatterns = [
    path('', views.users_dashboard, name='users_dashboard'),
    path('auth/', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('audit/', views.audit_dashboard, name='audit_dashboard'),
]
