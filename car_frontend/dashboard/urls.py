from django.urls import path
from . import views

urlpatterns = [
    path('', views.users_dashboard, name='users_dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('audit/', views.audit_dashboard, name='audit_dashboard'),
]