from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'user_roles', UserRoleViewSet)
router.register(r'makes', MakeViewSet)
router.register(r'models', ModelViewSet)
router.register(r'cars', CarViewSet)
router.register(r'car_images', CarImageViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'audit_logs', AuditLogViewSet)
router.register(r'register', RegisterViewSet, basename='Зарегай полупокера')

urlpatterns = [
    path('', include(router.urls)),
]
