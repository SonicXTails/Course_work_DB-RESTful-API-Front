from rest_framework.viewsets import ModelViewSet
from .models import *
from .serializers import *

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class UserRoleViewSet(ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer

class MakeViewSet(ModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer

class ModelViewSet(ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = ModelSerializer

class CarViewSet(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer

class CarImageViewSet(ModelViewSet):
    queryset = CarImage.objects.all()
    serializer_class = CarImageSerializer

class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

class AuditLogViewSet(ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer