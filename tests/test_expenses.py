from decimal import Decimal
import pytest
from app.models import AuditLog, Category, ExpenseStatus
from tests.factories import auth_header, make_expense

VALID = {"amount": "450.75", "category": "travel", "description": "Cab to client office"}


def submit(client, user, payload=None):
    return client.post("/expenses", json=payload or VALID, headers=auth_header(user))


def test_employee_can_submit_expense(client, employee):
    response = submit(client, employee)
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("450.75")
    assert body["category"] == "travel"
    assert body["status"] == "pending"
    assert body["employee_id"] == employee.id


def test_server_sets_owner_and_status_not_the_client(client, employee, other_employee):
    payload = {**VALID, "employee_id": other_employee.id, "status": "approved"}
    response = submit(client, employee, payload)
    assert response.status_code == 201
    body = response.json()
    assert body["employee_id"] == employee.id
    assert body["status"] == "pending"


def test_submit_creates_audit_entry(client, db_session, employee):
    expense_id = submit(client, employee).json()["id"]
    rows = db_session.query(AuditLog).filter_by(expense_id=expense_id).all()
    assert len(rows) == 1
    assert rows[0].action == "submitted"
    assert rows[0].actor_id == employee.id
    assert rows[0].old_status is None
    assert rows[0].new_status == "pending"


def test_submit_without_token(client):
    response = client.post("/expenses", json=VALID)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {**VALID, "amount": "0"},
        {**VALID, "amount": "-5"},
        {**VALID, "amount": "10.999"},
        {**VALID, "amount": "abc"},
        {**VALID, "amount": "1000000000000"},
        {**VALID, "category": "vacation"},
        {**VALID, "description": "x" * 501},
        {"category": "travel", "description": "no amount"},
    ],
    ids=[
        "zero-amount",
        "negative-amount",
        "three-decimals",
        "not-a-number",
        "too-many-digits",
        "unknown-category",
        "description-too-long",
        "missing-amount",
    ],
)
def test_invalid_expense_is_rejected(client, employee, payload):
    response = submit(client, employee, payload)
    assert response.status_code == 422


# ---------- listing my expenses ----------

def test_list_returns_only_own_expenses(client, db_session, employee, other_employee):
    mine = make_expense(db_session, employee.id)
    make_expense(db_session, other_employee.id)
    response = client.get("/expenses", headers=auth_header(employee))
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [mine.id]


def test_list_filter_by_status(client, db_session, employee):
    pending = make_expense(db_session, employee.id)
    approved = make_expense(db_session, employee.id)
    approved.status = ExpenseStatus.approved
    db_session.flush()
    response = client.get("/expenses?status=approved", headers=auth_header(employee))
    assert [item["id"] for item in response.json()] == [approved.id]
    assert pending.id not in [item["id"] for item in response.json()]


def test_list_filter_by_category(client, db_session, employee):
    make_expense(db_session, employee.id, category=Category.travel)
    meals = make_expense(db_session, employee.id, category=Category.meals)
    response = client.get("/expenses?category=meals", headers=auth_header(employee))
    assert [item["id"] for item in response.json()] == [meals.id]


def test_list_pagination(client, db_session, employee):
    for _ in range(3):
        make_expense(db_session, employee.id)
    first_page = client.get("/expenses?limit=2", headers=auth_header(employee))
    second_page = client.get("/expenses?limit=2&offset=2", headers=auth_header(employee))
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_bad_paging_values_are_rejected(client, employee, query):
    response = client.get(f"/expenses?{query}", headers=auth_header(employee))
    assert response.status_code == 422


def test_list_without_token(client):
    response = client.get("/expenses")
    assert response.status_code == 401


# ---------- viewing one expense ----------

def test_owner_can_get_expense(client, db_session, employee):
    expense = make_expense(db_session, employee.id)
    response = client.get(f"/expenses/{expense.id}", headers=auth_header(employee))
    assert response.status_code == 200
    assert response.json()["id"] == expense.id


def test_manager_can_get_team_members_expense(client, db_session, manager, employee):
    expense = make_expense(db_session, employee.id)
    response = client.get(f"/expenses/{expense.id}", headers=auth_header(manager))
    assert response.status_code == 200


def test_other_employee_gets_404(client, db_session, employee, other_employee):
    expense = make_expense(db_session, employee.id)
    response = client.get(f"/expenses/{expense.id}", headers=auth_header(other_employee))
    assert response.status_code == 404


def test_manager_of_another_team_gets_404(client, db_session, employee, other_manager):
    expense = make_expense(db_session, employee.id)
    response = client.get(f"/expenses/{expense.id}", headers=auth_header(other_manager))
    assert response.status_code == 404


def test_missing_expense_gets_404(client, employee):
    response = client.get("/expenses/999999", headers=auth_header(employee))
    assert response.status_code == 404


def test_get_expense_without_token(client, db_session, employee):
    expense = make_expense(db_session, employee.id)
    response = client.get(f"/expenses/{expense.id}")
    assert response.status_code == 401


# ---------- team list ----------

def test_team_list_shows_only_own_team(client, db_session, manager, employee, other_employee):
    team_expense = make_expense(db_session, employee.id)
    make_expense(db_session, other_employee.id)
    response = client.get("/expenses/team", headers=auth_header(manager))
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [team_expense.id]


def test_team_list_requires_manager(client, employee):
    response = client.get("/expenses/team", headers=auth_header(employee))
    assert response.status_code == 403


def test_team_list_status_filter(client, db_session, manager, employee):
    make_expense(db_session, employee.id)
    approved = make_expense(db_session, employee.id)
    approved.status = ExpenseStatus.approved
    db_session.flush()
    response = client.get("/expenses/team?status=pending", headers=auth_header(manager))
    assert approved.id not in [item["id"] for item in response.json()]
    assert len(response.json()) == 1


# ---------- history ----------

def test_history_shows_submission(client, employee):
    expense_id = submit(client, employee).json()["id"]
    response = client.get(f"/expenses/{expense_id}/history", headers=auth_header(employee))
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["action"] == "submitted"


def test_history_hidden_from_other_employee(client, db_session, employee, other_employee):
    expense = make_expense(db_session, employee.id)
    response = client.get(f"/expenses/{expense.id}/history", headers=auth_header(other_employee))
    assert response.status_code == 404


def test_history_of_missing_expense(client, employee):
    response = client.get("/expenses/999999/history", headers=auth_header(employee))
    assert response.status_code == 404