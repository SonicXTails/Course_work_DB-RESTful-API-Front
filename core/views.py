from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .serializers import *
from .permissions import IsAdmin
from django.db import transaction
from .models import *

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Создание пользователей через этот endpoint запрещено"}, status=403)

class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdmin]

class UserRoleViewSet(ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAdmin]

class MakeViewSet(ModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer
    permission_classes = [IsAdmin]

class ModelViewSet(ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    permission_classes = [IsAdmin]

class CarViewSet(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = [IsAdmin]

class CarImageViewSet(ModelViewSet):
    queryset = CarImage.objects.all()
    serializer_class = CarImageSerializer
    permission_classes = [IsAdmin]

class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdmin]

class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAdmin]

class AuditLogViewSet(ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]

class RegisterViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    http_method_names = ['post']  # разрешаем только POST

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"id": user.id, "username": user.username},
            status=status.HTTP_201_CREATED
        )

class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = serializer.validated_data['order']
        amount = serializer.validated_data['amount']

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
                    return Response(
                        TransactionSerializer(transaction_instance).data,
                        status=400
                    )

                transaction_instance = serializer.save(status=Transaction.Status.COMPLETED)
                order.status = Order.Status.PAID
                order.save()

            return Response(TransactionSerializer(transaction_instance).data, status=201)

        except Order.DoesNotExist:
            return Response({"detail": "Заказ не найден"}, status=404)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
