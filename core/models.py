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
    VIN = models.CharField(max_length=17, primary_key=True)
    seller = models.ForeignKey(User, related_name='sold_cars', on_delete=models.SET_NULL, null=True)
    make = models.ForeignKey(Make, on_delete=models.PROTECT)
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="available")
    created_at = models.DateTimeField(auto_now_add=True)

class CarImage(models.Model):
    car = models.ForeignKey(Car, related_name='images', on_delete=models.CASCADE)
    image_url = models.URLField()

class Order(models.Model):
    buyer = models.ForeignKey(User, related_name='purchases', on_delete=models.SET_NULL, null=True)
    car = models.ForeignKey(Car, related_name='orders', on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="pending")

class Transaction(models.Model):
    order = models.ForeignKey(Order, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="pending")

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