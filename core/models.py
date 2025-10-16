from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="custom_user_groups",
        related_query_name="custom_user_group",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_permissions",
        related_query_name="custom_user_permission",
    )

    @property
    def roles(self):
        return self.userrole_set.values_list('role__name', flat=True)

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

class Make(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Model(models.Model):
    make = models.ForeignKey(Make, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['make', 'name'], name='uniq_model_per_make'),
        ]

    def __str__(self):
        return f"{self.make_id}:{self.name}"

class Car(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        UNAVAILABLE = "unavailable", "Unavailable"

    VIN = models.CharField(max_length=17, primary_key=True)
    seller = models.ForeignKey(User, related_name='sold_cars', on_delete=models.SET_NULL, null=True)
    make = models.ForeignKey(Make, on_delete=models.PROTECT)
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.VIN} - {self.status}"

class CarImage(models.Model):
    car = models.ForeignKey(Car, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='car_images/', default='car_images/default.png')

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    buyer = models.ForeignKey(User, related_name='purchases', on_delete=models.SET_NULL, null=True)
    car = models.ForeignKey(Car, related_name='orders', on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        if self.buyer and self.car and self.buyer == self.car.seller:
            raise ValueError("Нельзя сделать заказ на собственную машину")

        if self._state.adding:
            active_order_exists = Order.objects.filter(
                car=self.car,
                status__in=[Order.Status.PENDING, Order.Status.PAID]
            ).exists()
            if active_order_exists:
                raise ValueError("У этой машины уже есть активный заказ")

            self.total_amount = self.car.price
            self.car.status = Car.Status.RESERVED
            self.car.save()

        else:
            if self.status == self.Status.PAID:
                self.car.status = Car.Status.SOLD
            elif self.status == self.Status.CANCELLED:
                self.car.status = Car.Status.AVAILABLE
            self.car.save()

        super().save(*args, **kwargs)


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(Order, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def save(self, *args, **kwargs):
        if self._state.adding:
            order = Order.objects.select_for_update().get(pk=self.order.pk)

            if order.status == Order.Status.CANCELLED:
                raise ValueError("Нельзя провести транзакцию для отменённого заказа")
            if order.status == Order.Status.PAID:
                raise ValueError("Заказ уже оплачен")

            if self.amount != order.total_amount:
                self.status = self.Status.FAILED
                order.car.status = Car.Status.AVAILABLE
                order.car.save()
            else:
                self.status = self.Status.COMPLETED
                order.status = Order.Status.PAID
                order.car.status = Car.Status.SOLD
                order.car.save()
                order.save()

        super().save(*args, **kwargs)


class Review(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_written")
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['author', 'target'], name='unique_review_per_user'),
        ]

    def clean(self):
        if self.author == self.target:
            raise ValidationError("Нельзя оставить отзыв самому себе!")

        if not 1 <= self.rating <= 5:
            raise ValidationError("Рейтинг должен быть от 1 до 5!")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Отзыв {self.author} → {self.target} ({self.rating})"

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    actor_label = models.CharField(max_length=150, blank=True, null=True)
    action = models.CharField(max_length=100)
    table_name = models.CharField(max_length=50)
    record_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    action_time = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-action_time']
        indexes = [
            models.Index(fields=['-action_time']),
            models.Index(fields=['table_name']),
            models.Index(fields=['action']),
        ]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_masked = models.CharField(max_length=32, blank=True) 

class UserSettings(models.Model):
    class Theme(models.TextChoices):
        SYSTEM = "system", "System"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    class DateFormat(models.TextChoices):
        ISO = "YYYY-MM-DD", "YYYY-MM-DD"
        RU = "DD.MM.YYYY", "DD.MM.YYYY"
        US = "MM/DD/YYYY", "MM/DD/YYYY"

    class NumberFormat(models.TextChoices):
        EU = "1 234,56", "1 234,56"
        US = "1,234.56", "1,234.56"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settings")
    theme = models.CharField(max_length=10, choices=Theme.choices, default=Theme.DARK)
    date_format = models.CharField(max_length=12, choices=DateFormat.choices, default=DateFormat.RU)
    number_format = models.CharField(max_length=12, choices=NumberFormat.choices, default=NumberFormat.EU)
    page_size = models.PositiveSmallIntegerField(default=20, validators=[MinValueValidator(5), MaxValueValidator(200)])
    saved_filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(page_size__gte=5) & models.Q(page_size__lte=200),
                name="usersettings_page_size_range",
            ),
        ]

    def __str__(self):
        return f"Settings<{self.user_id}>"

class BackupFile(models.Model):
    class Method(models.TextChoices):
        PG_DUMP = "pg_dump", "pg_dump"
        FIXTURES = "fixtures", "fixtures"

    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        SUCCESS = "success", "success"
        FAILED  = "failed", "failed"

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    method = models.CharField(max_length=16, choices=Method.choices, default=Method.PG_DUMP)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    file_path = models.CharField(max_length=512, blank=True, default="")
    file_size = models.BigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="")
    log = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.id} {self.method} {self.status} {self.created_at:%Y-%m-%d %H:%M}"
    
class BackupConfig(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_run_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = "Настройки бэкапов"
        verbose_name_plural = "Настройки бэкапов"

    def __str__(self):
        return f"BackupConfig(last_run_at={self.last_run_at})"
    
class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    # Предполагается, что у Car PK = VIN (как в ваших вьюсетах).
    car  = models.ForeignKey("core.Car", on_delete=models.CASCADE, related_name="in_favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "car")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["car"]),
        ]
        db_table = "core_favorite"

    def __str__(self):
        return f"{self.user_id} → {getattr(self.car, 'VIN', self.car_id)}"