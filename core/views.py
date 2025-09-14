from django.db import transaction
from django.utils.decorators import method_decorator

from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema

from .serializers import (
    UserSerializer, RoleSerializer, UserRoleSerializer,
    MakeSerializer, ModelSerializer, CarSerializer, CarImageSerializer,
    OrderSerializer, TransactionSerializer, ReviewSerializer,
    AuditLogSerializer, RegisterSerializer,
)
from .models import (
    User, Role, UserRole, Make, Model, Car, CarImage,
    Order, Transaction, Review, AuditLog,
)
from core.permissions import IsAdminOrReadOnlyAuthenticated, IsOwnerOrAdminForWrite


# ---------------------------
# Пользователи
# ---------------------------
@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Auth / Users']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Auth / Users']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Auth / Users']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Auth / Users']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Auth / Users']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Auth / Users']))
class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        elif self.action in ["list", "retrieve"]:
            return [IsAdminUser()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Создание пользователей через этот endpoint запрещено"},
            status=403
        )

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsAuthenticated])
    def me(self, request):
        """Эндпоинт /users/me/ — возвращает данные текущего юзера"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# ---------------------------
# Роли и назначение ролей
# ---------------------------
@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Admin / Roles']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Admin / Roles']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Admin / Roles']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Admin / Roles']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Admin / Roles']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Admin / Roles']))
class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]


@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Admin / User Roles']))
class UserRoleViewSet(ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_superuser or ('admin' in getattr(u, 'roles', [])):
            return qs
        return qs.filter(user=u.id)


# ---------------------------
# Каталог марок/моделей
# ---------------------------
@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Catalog / Makes']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Catalog / Makes']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Catalog / Makes']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Catalog / Makes']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Catalog / Makes']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Catalog / Makes']))
class MakeViewSet(ModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]


@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Catalog / Models']))
class VehicleModelViewSet(ModelViewSet):
    """Вьюсет для модели Model (переименован, чтобы не конфликтовать с DRF.ModelViewSet)."""
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]


# ---------------------------
# Машины и картинки
# ---------------------------
@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Cars']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Cars']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Cars']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Cars']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Cars']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Cars']))
class CarViewSet(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)


@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Cars / Images']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Cars / Images']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Cars / Images']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Cars / Images']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Cars / Images']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Cars / Images']))
class CarImageViewSet(ModelViewSet):
    queryset = CarImage.objects.all()
    serializer_class = CarImageSerializer
    permission_classes = [AllowAny]


# ---------------------------
# Заказы / Транзакции / Отзывы
# ---------------------------
@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Orders']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Orders']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Orders']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Orders']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Orders']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Orders']))
class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)


@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Payments']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Payments']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Payments']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Payments']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Payments']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Payments']))
class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = serializer.validated_data['order']
        amount = serializer.validated_data['amount']
        status_override = serializer.validated_data.get('status', None)

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order.pk)

                if order.status == Order.Status.CANCELLED:
                    return Response({"detail": "Нельзя провести транзакцию для отменённого заказа"}, status=400)

                if order.status == Order.Status.PAID:
                    return Response({"detail": "Заказ уже оплачен"}, status=400)

                if amount != order.total_amount:
                    transaction_instance = Transaction.objects.create(
                        order=order,
                        amount=amount,
                        status=Transaction.Status.FAILED
                    )
                    order.car.status = Car.Status.AVAILABLE
                    order.car.save()
                    return Response(
                        TransactionSerializer(transaction_instance).data,
                        status=400
                    )

                if status_override == Transaction.Status.CANCELLED:
                    transaction_instance = serializer.save(status=Transaction.Status.CANCELLED)
                    order.car.status = Car.Status.AVAILABLE
                    order.car.save()
                    return Response(TransactionSerializer(transaction_instance).data, status=200)

                transaction_instance = serializer.save(status=Transaction.Status.COMPLETED)
                order.status = Order.Status.PAID
                order.car.status = Car.Status.SOLD
                order.car.save()
                order.save()

            return Response(TransactionSerializer(transaction_instance).data, status=201)

        except Order.DoesNotExist:
            return Response({"detail": "Заказ не найден"}, status=404)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Reviews']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Reviews']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Reviews']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Reviews']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Reviews']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Reviews']))
class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# ---------------------------
# Аудит: публичный и админский (чистый)
# ---------------------------

@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Admin / Audit']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Admin / Audit']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Admin / Audit']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Admin / Audit']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Admin / Audit']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Admin / Audit']))
class AuditLogViewSet(ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]


class AuditLogAdminViewSet(ModelViewSet):
    """
    Чистый админский вьюсет для /api/v1/admin/audit_logs/ БЕЗ swagger-декораторов.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]


# ---------------------------
# Регистрация
# ---------------------------
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Auth']))
class RegisterViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user_role, _ = Role.objects.get_or_create(name='user')
        UserRole.objects.get_or_create(user=user, role=user_role)

        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {"id": user.id, "username": user.username, "token": token.key},
            status=status.HTTP_201_CREATED
        )