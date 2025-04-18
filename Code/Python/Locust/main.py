from locust import HttpUser, task, between
import json
import random

class SpringApiUser(HttpUser):
    wait_time = between(1, 3)  # Wait between 1-3s between tasks

    @task(3)
    def get_users(self):
        self.client.get("/api/users")

    @task(1)
    def create_user(self):
        user_data = {
            "name": f"TestUser{random.randint(1, 10000)}",
            "email": f"user{random.randint(1, 10000)}@example.com"
        }
        headers = {"Content-Type": "application/json"}
        self.client.post("/api/users", data=json.dumps(user_data), headers=headers)
