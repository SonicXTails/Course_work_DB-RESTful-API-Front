from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import bootstrap, UserViewSet, RoleViewSet, UserRoleViewSet, MakeViewSet, VehicleModelViewSet, CarViewSet, CarImageViewSet, OrderViewSet, TransactionViewSet, ReviewViewSet, AuditLogViewSet, AuditLogAdminViewSet, RegisterViewSet

root = DefaultRouter()
root.register(r'users', UserViewSet, basename='user')
root.register(r'makes', MakeViewSet, basename='make')
root.register(r'models', VehicleModelViewSet, basename='model')
root.register(r'cars', CarViewSet, basename='car')
root.register(r'car_images', CarImageViewSet, basename='carimage')
root.register(r'orders', OrderViewSet, basename='order')
root.register(r'transactions', TransactionViewSet, basename='transaction')
root.register(r'reviews', ReviewViewSet, basename='review')
root.register(r'audit_logs', AuditLogViewSet, basename='auditlog')

public = DefaultRouter()
public.register(r'cars', CarViewSet, basename='car-public')
public.register(r'car_images', CarImageViewSet, basename='carimage-public')
public.register(r'makes', MakeViewSet, basename='make-public')
public.register(r'models', VehicleModelViewSet, basename='model-public')

admin = DefaultRouter()
admin.register(r'roles', RoleViewSet, basename='role')
admin.register(r'user_roles', UserRoleViewSet, basename='userrole')
admin.register(r'audit_logs', AuditLogAdminViewSet, basename='auditlog-admin')

auth = DefaultRouter()
auth.register(r'register', RegisterViewSet, basename='register')
auth.register(r'users', UserViewSet, basename='user-auth')

urlpatterns = [
    path('', include(root.urls)),
    path('public/', include(public.urls)),
    path('admin/', include(admin.urls)),
    path('auth/', include(auth.urls)),
    path('bootstrap/', bootstrap, name='bootstrap'), 
]