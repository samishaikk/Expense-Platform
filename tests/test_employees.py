import pytest

from tests.factories import auth_header

VALID_PAYLOAD = {
    "name": "Priya Employee",
    "email": "priya@example.com",
    "password": "password123",
    "role": "employee",
}


def test_manager_can_create_employee(client, manager):
    payload = {**VALID_PAYLOAD, "manager_id": manager.id}
    response = client.post("/employees", json=payload, headers=auth_header(manager))
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "priya@example.com"
    assert body["role"] == "employee"
    assert body["manager_id"] == manager.id
    assert "password" not in body
    assert "password_hash" not in body


def test_created_employee_can_log_in(client, manager):
    created = client.post("/employees", json=VALID_PAYLOAD, headers=auth_header(manager))
    assert created.status_code == 201
    response = client.post(
        "/auth/login",
        data={"username": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    )
    assert response.status_code == 200


def test_create_employee_without_token(client):
    response = client.post("/employees", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_employee_cannot_create_employee(client, employee):
    response = client.post("/employees", json=VALID_PAYLOAD, headers=auth_header(employee))
    assert response.status_code == 403


def test_duplicate_email_is_rejected(client, manager, employee):
    payload = {**VALID_PAYLOAD, "email": employee.email}
    response = client.post("/employees", json=payload, headers=auth_header(manager))
    assert response.status_code == 409


def test_manager_id_must_exist(client, manager):
    payload = {**VALID_PAYLOAD, "manager_id": 999999}
    response = client.post("/employees", json=payload, headers=auth_header(manager))
    assert response.status_code == 400


def test_manager_id_must_belong_to_a_manager(client, manager, employee):
    payload = {**VALID_PAYLOAD, "manager_id": employee.id}
    response = client.post("/employees", json=payload, headers=auth_header(manager))
    assert response.status_code == 400


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "not-an-email"},
        {"password": "short"},
        {"password": "x" * 73},
        {"role": "boss"},
        {"name": ""},
    ],
    ids=["bad-email", "short-password", "password-too-long", "unknown-role", "empty-name"],
)
def test_invalid_payload_is_rejected(client, manager, changes):
    payload = {**VALID_PAYLOAD, **changes}
    response = client.post("/employees", json=payload, headers=auth_header(manager))
    assert response.status_code == 422


def test_manager_lists_only_own_team(client, manager, employee, other_employee):
    response = client.get("/employees", headers=auth_header(manager))
    assert response.status_code == 200
    emails = [person["email"] for person in response.json()]
    assert emails == [employee.email]


def test_employee_cannot_list_team(client, employee):
    response = client.get("/employees", headers=auth_header(employee))
    assert response.status_code == 403