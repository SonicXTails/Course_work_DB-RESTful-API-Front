
import os
import pytest
import requests

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("API_BASE_URL", "http://localhost:8000")

def auth_headers(token: str | None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Token {token}"
    return h

@pytest.fixture(scope="session")
def tokens():
    return {
        "admin": os.getenv("ADMIN_TOKEN", ""),
        "user": os.getenv("USER_TOKEN", ""),
        "analyst": os.getenv("ANALYST_TOKEN", ""),
    }

@pytest.fixture
def h_admin(tokens):
    return auth_headers(tokens["admin"])

@pytest.fixture
def h_user(tokens):
    return auth_headers(tokens["user"])

@pytest.fixture
def h_analyst(tokens):
    return auth_headers(tokens["analyst"])
