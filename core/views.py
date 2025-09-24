from django.db import transaction
from django.utils.decorators import method_decorator

from rest_framework.authentication import TokenAuthentication
from core.authentication import CsrfExemptSessionAuthentication
from PIL import Image
from rest_framework.viewsets import ModelViewSet as DRFModelViewSet
from core.db import call_proc
from django.db import models
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from django.db import connection, transaction 
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework import status
from core.viewsets import AuditModelViewSet as ModelViewSet
from django.utils import timezone
from datetime import timedelta
from .models import Order, Transaction, Car
from rest_framework.permissions import BasePermission

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

class IsSuperuserOrRoleAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.is_superuser:
            return True
        return UserRole.objects.filter(user=u, role__name__iexact="admin").exists()

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Prefetch



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bootstrap(request):
    user = request.user

    cars_qs = (
        Car.objects
        .select_related("make", "model")
        .prefetch_related(Prefetch("images", queryset=CarImage.objects.only("id", "car", "image")))
        .only("VIN", "make", "model", "year", "price", "status", "seller", "created_at")
    )

    makes  = list(Make.objects.only("id", "name").values("id", "name"))
    models = list(Model.objects.only("id", "name", "make").values("id", "name", "make"))
    cars   = list(cars_qs.values("VIN", "make", "model", "year", "price", "status", "seller", "created_at"))

    imgs = []
    for i in CarImage.objects.only("id", "car", "image").iterator():
        try:
            url = i.image.url
            abs_url = request.build_absolute_uri(url)
        except Exception:
            abs_url = request.build_absolute_uri(settings.MEDIA_URL + str(i.image))
        imgs.append({"id": i.id, "car": getattr(i, "car_id", None), "image": abs_url})

    data = {
        "me": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "is_staff": getattr(user, "is_staff", False),
        },
        "makes": makes,
        "models": models,
        "cars": cars,
        "car_images": imgs,
    }
    return Response(data)

# ---------------------------
# Пользователи
# ---------------------------
@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Admin / User Roles']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Admin / User Roles']))
class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        elif self.action in ["list", "retrieve"]:
            return [IsSuperuserOrRoleAdmin()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Создание пользователей через этот endpoint запрещено"}, status=403)

    @action(detail=False, methods=["get", "patch", "put"], url_path="me", permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        GET  /users/me/          -> вернуть себя
        PATCH/PUT /users/me/     -> частично/полностью обновить свои данные
        """
        user = request.user
        if request.method.lower() == "get":
            return Response(self.get_serializer(user).data)

        partial = request.method.lower() == "patch"
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


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

    authentication_classes = [TokenAuthentication, CsrfExemptSessionAuthentication]
    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_superuser or ('admin' in getattr(u, 'roles', [])):
            return qs
        return qs.filter(user=u.id)

    @method_decorator(csrf_exempt, name='dispatch') 
    @action(detail=False, methods=['post'], url_path='assign',
            permission_classes=[IsSuperuserOrRoleAdmin])
    def assign(self, request):
        user_id = request.data.get('user')
        role_id = request.data.get('role')
        if not user_id or not role_id:
            return Response({"detail": "user и role обязательны"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
            role = Role.objects.get(pk=role_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:
            return Response({"detail": "Роль не найдена"}, status=status.HTTP_404_NOT_FOUND)

        UserRole.objects.filter(user=user).delete()
        link = UserRole.objects.create(user=user, role=role)
        return Response({"id": link.id, "user": link.user.id, "role": link.role.id}, status=status.HTTP_200_OK)


@method_decorator(name='list',           decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='retrieve',       decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='create',         decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='update',         decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Catalog / Models']))
@method_decorator(name='destroy',        decorator=swagger_auto_schema(tags=['Catalog / Models']))
class VehicleModelViewSet(ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


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
    queryset = (Car.objects
        .select_related("make","model")
        .prefetch_related(Prefetch("images", queryset=CarImage.objects.only("id","car","image")))
        .only("VIN","make","model","year","price","status")
    )
    serializer_class = CarSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    def get_queryset(self):
        qs = (Car.objects
              .select_related("make", "model")
              .prefetch_related(Prefetch("images", queryset=CarImage.objects.only("id","car","image"))))

        if getattr(self, 'action', None) in ("list", "retrieve"):
            return qs.only("VIN","make","model","year","price","status")
        return qs
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    @action(
        detail=True,
        methods=['post'],
        url_path='images',
        parser_classes=[MultiPartParser],
        permission_classes=[IsAuthenticated],
    )
    def upload_images(self, request, pk=None):
        try:
            car = Car.objects.get(pk=pk)
        except Car.DoesNotExist:
            return Response({"detail": "Машина не найдена"}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist('files')
        if not files and 'image' in request.FILES:
            files = [request.FILES['image']]
        if not files:
            return Response({"detail": "Файлы не переданы. Используй 'files' или 'image'."}, status=400)

        created = []
        for f in files:
            if f.size > 8 * 1024 * 1024:
                return Response({"detail": f"Слишком большой файл: {f.name} (>8MB)"}, status=400)
            try:
                im = Image.open(f)
                w, h = im.size
                ratio = (w / h) if h else 0
            except Exception:
                return Response({"detail": f"Не удалось прочитать изображение: {getattr(f,'name','file')}"}, status=400)

            if w < 800 or h < 450 or ratio < 1.3:
                return Response({"detail": f"Недопустимое фото {getattr(f,'name','')}: только горизонтальные ≥800×450, соотношение ≥1.3"}, status=400)

            try: f.seek(0)
            except Exception: pass

            img = CarImage.objects.create(car=car, image=f)
            created.append(CarImageSerializer(img, context={"request": request}).data)

        return Response(created, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reserve', permission_classes=[IsAuthenticated])
    def reserve(self, request, pk=None):
        order_id = call_proc("SELECT sp_reserve_car(%s, %s);", [request.user.id, pk])
        order = Order.objects.get(pk=order_id)
        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)

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
    """
    Заказы.

    Видимость:
      - Админ видит все.
      - Обычный пользователь видит:
          * свои покупки (buyer == request.user)
          * заказы на свои машины (car.seller == request.user).
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    # ---------- READ SCOPE ----------
    def get_queryset(self):
        u = self.request.user
        qs = (Order.objects
              .select_related('car', 'buyer')
              .only('id', 'status', 'order_date', 'total_amount', 'car', 'buyer'))
        if not (u and u.is_authenticated):
            return qs.none()

        is_admin = bool(u.is_superuser or ('admin' in getattr(u, 'roles', [])))
        if is_admin:
            return qs
        return qs.filter(Q(buyer=u) | Q(car__seller=u))

    # ---------- CREATE ----------
    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

    # ---------- CANCEL BY DB FUNCTION (IF YOU USE IT) ----------
    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel_via_sp(self, request, pk=None):
        """
        Отмена заказа через БД-функцию `sp_cancel_reservation(order_id, reason)`.
        POST /api/v1/orders/{id}/cancel/ {"reason": "..."}
        """
        reason = request.data.get('reason')
        call_proc("SELECT sp_cancel_reservation(%s, %s);", [pk, reason])
        obj = Order.objects.get(pk=pk)
        return Response(OrderSerializer(obj, context={'request': request}).data, status=status.HTTP_200_OK)

    # ---------- SELLER CANCEL ----------
    @action(detail=True, methods=['post'], url_path='seller_cancel', permission_classes=[IsAuthenticated])
    def seller_cancel(self, request, pk=None):
        """
        Продавец (car.seller) или админ отменяет PENDING-заказ.
        Возвращает Order.
        """
        order = self.get_object()
        u = request.user
        is_admin = bool(u and u.is_authenticated and (u.is_superuser or ('admin' in getattr(u, 'roles', []))))

        if not (is_admin or (order.car and getattr(order.car, 'seller_id', None) == u.id)):
            return Response({"detail": "Только продавец или админ может отменить заказ."},
                            status=status.HTTP_403_FORBIDDEN)

        if order.status != Order.Status.PENDING:
            return Response({"detail": "Можно отменить только PENDING-заказ."},
                            status=status.HTTP_400_BAD_REQUEST)

        reason = (request.data.get('reason') or '').strip()

        with transaction.atomic():
            ord_locked = (
                Order.objects.select_for_update(of=('self',))
                .select_related('car')
                .get(pk=order.pk)
            )

            if ord_locked.status != Order.Status.PENDING:
                return Response({"detail": "Заказ уже не PENDING."}, status=status.HTTP_409_CONFLICT)

            # 1) Отменяем заказ
            ord_locked.status = Order.Status.CANCELLED
            ord_locked.save(update_fields=['status'])

            # 2) Отменяем все незавершённые транзакции
            Transaction.objects.filter(
                order=ord_locked,
                status=Transaction.Status.PENDING
            ).update(status=Transaction.Status.CANCELLED)

            # 3) Возвращаем авто в продажу
            if ord_locked.car and ord_locked.car.status != Car.Status.AVAILABLE:
                ord_locked.car.status = Car.Status.AVAILABLE
                ord_locked.car.save(update_fields=['status'])

            # 4) Аудит (по желанию)
            try:
                AuditLog.objects.create(
                    user=u,
                    action="order_cancelled_by_seller",
                    object_type="Order",
                    object_id=str(ord_locked.pk),
                    details={"reason": reason} if reason else {}
                )
            except Exception:
                pass

        return Response(OrderSerializer(ord_locked, context={'request': request}).data, status=status.HTTP_200_OK)

    # ---------- CONFIRM / COMPLETE SALE ----------
    @action(detail=True, methods=['post'], url_path='confirm', permission_classes=[IsAuthenticated])
    def confirm(self, request, pk=None):
        """
        Завершение продажи: вызывает sp_complete_sale(order_id),
        который создаёт Transaction и выставляет статусы.
        Возвращает созданную Transaction.
        """
        tx_id = call_proc("SELECT sp_complete_sale(%s);", [pk])
        tx = Transaction.objects.get(pk=tx_id)
        return Response(TransactionSerializer(tx, context={'request': request}).data, status=status.HTTP_201_CREATED)

    # ---------- OPTIONAL: CANCEL EXPIRED PENDING ORDERS ----------
    @action(detail=False, methods=['post'], url_path='cancel_expired', permission_classes=[IsAuthenticated])
    def cancel_expired(self, request):
        """
        Массовая отмена протухших PENDING-заказов (резерв 20 минут).
        Полезно для фронта, который «пингует» этот эндпоинт.
        Возвращает {cancelled: <int>}.
        """
        now = timezone.now()
        expired = (Order.objects
                   .select_related('car')
                   .filter(status=Order.Status.PENDING,
                           order_date__lte=now - timedelta(minutes=20)))

        cancelled_cnt = 0
        with transaction.atomic():
            # Лочим и обрабатываем партиями
            for ord_locked in expired.select_for_update(of=('self',)):
                # На случай гонок — перепроверка
                if ord_locked.status != Order.Status.PENDING:
                    continue

                ord_locked.status = Order.Status.CANCELLED
                ord_locked.save(update_fields=['status'])

                Transaction.objects.filter(
                    order=ord_locked,
                    status=Transaction.Status.PENDING
                ).update(status=Transaction.Status.CANCELLED)

                if ord_locked.car and ord_locked.car.status != Car.Status.AVAILABLE:
                    ord_locked.car.status = Car.Status.AVAILABLE
                    ord_locked.car.save(update_fields=['status'])

                cancelled_cnt += 1

        return Response({"cancelled": cancelled_cnt}, status=status.HTTP_200_OK)

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

                if order.status == Order.Status.PENDING:
                    deadline = order.order_date + timedelta(minutes=20)
                    if timezone.now() >= deadline:
                        order.status = Order.Status.CANCELLED
                        order.car.status = Car.Status.AVAILABLE
                        order.car.save()
                        order.save()
                        return Response(
                            {"detail": "Время резерва истекло. Заказ отменён."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

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
    permission_classes = [IsSuperuserOrRoleAdmin]

class AuditLogAdminViewSet(ModelViewSet):
    """
    Чистый админский вьюсет для /api/v1/admin/audit_logs/
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperuserOrRoleAdmin]


# ---------------------------
# Регистрация
# ---------------------------
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Auth']))
class RegisterViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    http_method_names = ['post']
    permission_classes = [AllowAny]

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
    
class MakeViewSet(ModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer
    permission_classes = [IsOwnerOrAdminForWrite]

    @action(detail=True, methods=["post"])
    def bulk_reprice(self, request, pk=None):
        raw = request.data.get("percent")
        try:
            percent = Decimal(str(raw))
        except (InvalidOperation, TypeError):
            return Response({"detail": "percent должен быть числом"}, status=400)

        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM core_car
                    WHERE make_id = %s
                      AND status IN ('available','reserved')
                """, [int(pk)])
                affected = int(cur.fetchone()[0])

                cur.execute("CALL sp_bulk_reprice(%s, %s)", [int(pk), percent])

        return Response({"affected": affected, "percent": float(percent)}, status=200)