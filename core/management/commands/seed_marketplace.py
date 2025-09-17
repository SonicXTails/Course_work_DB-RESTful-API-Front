# <your_app>/management/commands/seed_marketplace.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction as db_tx
from random import randint, random, choice, sample, seed as rnd_seed
from datetime import timedelta

from ...models import Role, UserRole, Make, Model, Car, Order, Transaction, Review

User = get_user_model()

MAKES_MODELS = {
    "Toyota": ["Camry", "Corolla", "RAV4"],
    "BMW": ["3 Series", "5 Series", "X3"],
    "Audi": ["A4", "A6", "Q5"],
    "Mercedes-Benz": ["C-Class", "E-Class", "GLC"],
    "Kia": ["Rio", "Sportage"],
    "Hyundai": ["Solaris", "Tucson"],
    "Volkswagen": ["Polo", "Tiguan"],
    "LADA": ["Vesta", "Granta"],
}

SELLER_NAMES = [
    ("alice", "Alice", "Ivanova"),
    ("bob", "Bob", "Petrov"),
    ("carol", "Carol", "Sidorova"),
    ("dave", "Dave", "Smirnov"),
    ("erin", "Erin", "Volkova"),
]

BUYER_NAMES = [
    ("mike", "Mikhail", "Orlov"),
    ("nina", "Nina", "Kuznetsova"),
    ("oleg", "Oleg", "Karpov"),
    ("pavel", "Pavel", "Denisov"),
    ("rita", "Rita", "Sorokina"),
]

REVIEW_TEXTS = [
    "Быстро договорились, всё чётко 👍",
    "Хороший продавец, машина соответствует описанию.",
    "Были мелкие недочёты, но в целом ок.",
    "Отличная сделка, рекомендую!",
    "Немного задержался, но потом всё оперативно оформили.",
]


class Command(BaseCommand):
    help = "Заполняет базу демо-данными маркетплейса (продавцы/покупатели, авто, заказы, транзакции, отзывы)."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true",
                            help="Очистить связанные таблицы перед заполнением.")
        parser.add_argument("--seed", type=int, default=42,
                            help="Seed для рандома (по умолчанию 42).")
        parser.add_argument("--cars", type=int, default=40,
                            help="Сколько машин создать (по умолчанию 40).")

    @db_tx.atomic
    def handle(self, *args, **opts):
        rnd_seed(opts["seed"])

        if opts["fresh"]:
            self.stdout.write("Удаляю старые данные…")
            Review.objects.all().delete()
            Transaction.objects.all().delete()
            Order.objects.all().delete()
            Car.objects.all().delete()
            Model.objects.all().delete()
            Make.objects.all().delete()
            # Пользователей и роли оставим — но почистим user-roles
            UserRole.objects.all().delete()

        # --- Роли ---
        role_admin, _ = Role.objects.get_or_create(name="admin")
        role_user,  _ = Role.objects.get_or_create(name="user")
        role_anal,  _ = Role.objects.get_or_create(name="analitic")

        # --- Пользователи ---
        def get_or_create_user(username, first, last, is_superuser=False, is_staff=False):
            u, created = User.objects.get_or_create(username=username, defaults={
                "first_name": first, "last_name": last,
                "is_superuser": is_superuser, "is_staff": is_staff,
                "email": f"{username}@example.com",
            })
            if created or not u.has_usable_password():
                u.set_password("123")  # общий тестовый пароль
                u.save()
            return u

        admin = get_or_create_user("admin", "Admin", "User", is_superuser=True, is_staff=True)
        UserRole.objects.get_or_create(user=admin, role=role_admin)

        sellers = [get_or_create_user(u, f, l) for (u, f, l) in SELLER_NAMES]
        buyers  = [get_or_create_user(u, f, l) for (u, f, l) in BUYER_NAMES]

        for u in sellers + buyers:
            UserRole.objects.get_or_create(user=u, role=role_user)
        # одному пользователю дадим роль аналитика
        UserRole.objects.get_or_create(user=sellers[0], role=role_anal)

        # --- Марки/модели ---
        make_map = {}
        model_map = {}
        for make_name, models in MAKES_MODELS.items():
            make, _ = Make.objects.get_or_create(name=make_name)
            make_map[make_name] = make
            for m in models:
                vm, _ = Model.objects.get_or_create(make=make, name=m)
                model_map[(make_name, m)] = vm

        now = timezone.now()
        cars_to_create = opts["cars"]

        self.stdout.write(f"Создаю ~{cars_to_create} авто, заказы, транзакции…")

        created_cars = []
        # создаём авто за последние 90 дней
        for i in range(cars_to_create):
            make_name = choice(list(MAKES_MODELS.keys()))
            model_name = choice(MAKES_MODELS[make_name])
            vm = model_map[(make_name, model_name)]
            make = make_map[make_name]
            seller = choice(sellers)

            year = randint(2012, 2023)
            base = {
                "make": make,
                "model": vm,
                "year": year,
                "seller": seller,
                "price": randint(400_000, 3_500_000),
                "status": Car.Status.AVAILABLE,
                "description": f"{make_name} {model_name}, {year} г.в. Тестовое объявление.",
            }

            # VIN как уникальная строка длиной 17 (условно)
            vin = f"DEMO{year}{i:05d}".ljust(17, "X")

            car = Car.objects.create(VIN=vin, **base)
            created_cars.append(car)

            # поправим дату создания в прошлое (0..90 дней назад)
            created_shift = randint(0, 90)
            Car.objects.filter(pk=car.pk).update(created_at=now - timedelta(days=created_shift))

        # --- Сделки: для ~70% машин создадим заказ, для ~50% из них — успешную оплату ---
        total_orders = 0
        total_paid = 0
        orders_for_reviews = []

        for car in created_cars:
            if random() < 0.70:
                buyer = choice(buyers)
                if buyer.id == getattr(car.seller, "id", None):
                    buyer = choice([b for b in buyers if b.id != getattr(car.seller, "id", None)])

                # заказ через API-логику модели: при создании Order статус авто станет RESERVED
                order = Order.objects.create(buyer=buyer, car=car, total_amount=car.price)
                total_orders += 1

                # откатим дату заказа на 0..30 дней после публикации
                car_refresh = Car.objects.get(pk=car.pk)
                base_created = car_refresh.created_at
                order_shift = randint(0, 30)
                Order.objects.filter(pk=order.pk).update(order_date=base_created + timedelta(days=order_shift))

                # часть заказов отменим (20%), часть оставим pending (30%), остальное оплатим (50%)
                r = random()
                if r < 0.20:
                    order.status = Order.Status.CANCELLED
                    order.save(update_fields=["status"])
                    # модель сама вернёт машину в AVAILABLE
                elif r < 0.50:
                    # оставляем PENDING (ничего не делаем)
                    pass
                else:
                    # оплачиваем: Transaction.save переведёт заказ в PAID и машину в SOLD
                    Transaction.objects.create(order=order, amount=order.total_amount)
                    total_paid += 1
                    orders_for_reviews.append(order)

        # --- Отзывы: каждый успешный покупатель оставит отзыв своему продавцу (не чаще 1 на пару) ---
        for order in sample(orders_for_reviews, k=max(1, len(orders_for_reviews)//2)):
            author = order.buyer
            target = order.car.seller
            if not author or not target or author.id == target.id:
                continue
            try:
                Review.objects.create(
                    author=author,
                    target=target,
                    rating=randint(3, 5),
                    comment=choice(REVIEW_TEXTS),
                )
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(
            f"Готово: авто={len(created_cars)}, заказы={total_orders}, оплачено={total_paid}, отзывы={Review.objects.count()}."
        ))
        self.stdout.write(self.style.WARNING("Тестовые логины: admin/alice/bob/... (пароль для всех: 123)"))