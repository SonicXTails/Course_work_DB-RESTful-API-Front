from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import BackupFile
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_superuser", "is_staff"]
        read_only_fields = ["id", "is_superuser", "is_staff"]

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
        fields = ["id", "name"]

class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Model
        fields = '__all__'

class CarSerializer(serializers.ModelSerializer):
    # отдаем картинки как URL'ы
    images = serializers.SerializerMethodField()

    # поля продавца
    seller_username   = serializers.CharField(source='seller.username',   read_only=True)
    seller_first_name = serializers.CharField(source='seller.first_name', read_only=True)
    seller_last_name  = serializers.CharField(source='seller.last_name',  read_only=True)
    seller_full_name  = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = [
            "VIN", "make", "model", "year", "price", "status",
            "description", "created_at",
            "images",
            "seller", "seller_username", "seller_first_name",
            "seller_last_name", "seller_full_name",
        ]
        read_only_fields = ("seller",)

    def get_images(self, obj):
        req = self.context.get("request")
        urls = []
        # если префетч был — не делаем доп. запросов
        for im in getattr(obj, "images", CarImage.objects.none()).all():
            try:
                url = im.image.url
            except Exception:
                url = settings.MEDIA_URL + str(im.image)
            urls.append(req.build_absolute_uri(url) if req else url)
        return urls

    def get_seller_full_name(self, obj):
        if not getattr(obj, "seller", None):
            return ""
        fn = (obj.seller.first_name or "").strip()
        ln = (obj.seller.last_name  or "").strip()
        full = (ln + " " + fn).strip()
        return full or (obj.seller.username or "")


class CarImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = CarImage
        fields = ["id", "car", "image"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and instance.image and hasattr(instance.image, "url"):
            data["image"] = request.build_absolute_uri(instance.image.url)
        return data

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['total_amount']

    def get_expires_in_seconds(self, obj):
        if obj.status != Order.Status.PENDING or not obj.order_date:
            return None
        deadline = obj.order_date + timedelta(minutes=20)
        delta = (deadline - timezone.now()).total_seconds()
        return max(0, int(delta))

    def create(self, validated_data):
        car = validated_data.get("car")
        buyer = validated_data.get("buyer")
        if buyer and car and buyer == car.seller:
            raise serializers.ValidationError("Нельзя сделать заказ на собственную машину")
        validated_data["total_amount"] = car.price
        return super().create(validated_data)

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'order', 'amount', 'transaction_date', 'status']
        read_only_fields = ['transaction_date']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['author', 'created_at']

class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
    
class BackupFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupFile
        fields = ["id", "created_at", "created_by", "method", "status", "file_size", "checksum_sha256", "log"]
        read_only_fields = fields

class FavoriteSerializer(serializers.ModelSerializer):
    # При создании принимаем VIN (slug_field='VIN'), на выходе отдаем ещё и сам объект машины
    car = serializers.SlugRelatedField(slug_field="VIN", queryset=Car.objects.all())
    car_obj = CarSerializer(source="car", read_only=True)

    class Meta:
        model  = Favorite
        fields = ("id", "car", "car_obj", "created_at")
        read_only_fields = ("id", "created_at")