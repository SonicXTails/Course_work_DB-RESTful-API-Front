from django.db import models
from django.contrib.auth.models import AbstractUser

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
        """Возвращает список названий ролей пользователя"""
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
    name = models.CharField(max_length=50, unique=True)

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
    reviewer = models.ForeignKey(User, related_name='given_reviews', on_delete=models.CASCADE)
    reviewed_user = models.ForeignKey(User, related_name='received_reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=100)
    table_name = models.CharField(max_length=50)
    record_id = models.IntegerField(null=True, blank=True)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    action_time = models.DateTimeField(auto_now_add=True)