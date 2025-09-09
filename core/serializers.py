from rest_framework import serializers
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'

class MakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Make
        fields = '__all__'

class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Model
        fields = '__all__'

class CarSerializer(serializers.ModelSerializer):
    images = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

    class Meta:
        model = Car
        fields = ('VIN', 'seller', 'make', 'model', 'year', 'price', 'status', 'created_at', 'images')

class CarImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarImage
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'