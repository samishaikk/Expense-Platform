from datetime import datetime, timedelta, timezone

import jwt

from app.security import ALGORITHM, SECRET_KEY, create_access_token
from tests.factories import TEST_PASSWORD, auth_header


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_login_success(client, employee):
    response = login(client, employee.email, TEST_PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, employee):
    response = login(client, employee.email, "wrong-password")
    assert response.status_code == 401


def test_login_unknown_email_gives_same_error_as_wrong_password(client, employee):
    wrong_password = login(client, employee.email, "wrong-password")
    unknown_email = login(client, "nobody@example.com", TEST_PASSWORD)
    assert unknown_email.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_me_returns_current_user(client, employee):
    response = client.get("/auth/me", headers=auth_header(employee))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == employee.email
    assert body["role"] == "employee"
    assert "password_hash" not in body


def test_me_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_with_expired_token(client, employee):
    expired = jwt.encode(
        {"sub": str(employee.id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_me_with_token_signed_with_wrong_key(client, employee):
    forged = jwt.encode(
        {"sub": str(employee.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        "some-other-secret",
        algorithm=ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_me_with_token_for_user_that_does_not_exist(client):
    token = create_access_token(999999)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401