
from locust import HttpUser, task, between
import os, random

class ApiUser(HttpUser):
    wait_time = between(0.2, 1.0)
    base_path = os.getenv("BASE_PATH", "/api/v1")
    token = os.getenv("LOAD_TOKEN", "")

    def on_start(self):
        self.headers = {"Authorization": f"Token {self.token}"} if self.token else {}

    @task(3)
    def list_cars(self):
        self.client.get(f"{self.base_path}/cars/?ordering=-price", headers=self.headers)

    @task(2)
    def filter_cars(self):
        make = random.choice(["Toyota","BMW","Audi","Ford"])
        self.client.get(f"{self.base_path}/cars/?make={make}&price__lte=1000000", headers=self.headers)

    @task(1)
    def view_car(self):
        car_id = random.randint(1, 200)
        self.client.get(f"{self.base_path}/cars/{car_id}/", headers=self.headers)

    @task(1)
    def create_order_if_admin(self):
        if not self.token:
            return
        body = {"car_id": 1, "customer_id": 1}
        self.client.post(f"{self.base_path}/orders/reserve/", json=body, headers={**self.headers, "Content-Type":"application/json"})
