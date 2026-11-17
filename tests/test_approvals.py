import pytest

from app.models import AuditLog, ExpenseStatus
from tests.factories import auth_header, make_expense


def decide(client, user, expense_id, body):
    return client.post(
        f"/expenses/{expense_id}/decision", json=body, headers=auth_header(user)
    )



def test_manager_can_approve_without_comment(client, db_session, manager, employee):
    expense = make_expense(db_session, employee.id)
    response = decide(client, manager, expense.id, {"decision": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.approved


def test_manager_can_reject_with_comment(client, db_session, manager, employee):
    expense = make_expense(db_session, employee.id)
    response = decide(
        client, manager, expense.id,
        {"decision": "rejected", "comment": "Missing receipt"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_decision_writes_audit_entry(client, db_session, manager, employee):
    expense = make_expense(db_session, employee.id)
    expense_id = expense.id
    response = decide(
        client, manager, expense_id,
        {"decision": "approved", "comment": "Within policy"},
    )
    assert response.status_code == 200
    row = db_session.query(AuditLog).filter_by(expense_id=expense_id).one()
    assert row.actor_id == manager.id
    assert row.actor_role == "manager"
    assert row.action == "approved"
    assert row.old_status == "pending"
    assert row.new_status == "approved"
    assert row.comment == "Within policy"


#- decisions that must be refused -

def test_second_decision_gets_409_and_adds_no_audit_row(client, db_session, manager, employee):
    expense = make_expense(db_session, employee.id)
    expense_id = expense.id
    first = decide(client, manager, expense_id, {"decision": "approved"})
    second = decide(client, manager, expense_id, {"decision": "approved"})
    assert first.status_code == 200
    assert second.status_code == 409
    rows = db_session.query(AuditLog).filter_by(expense_id=expense_id).all()
    assert len(rows) == 1


def test_rejected_expense_cannot_be_approved_later(client, db_session, manager, employee):
    expense = make_expense(db_session, employee.id)
    expense_id = expense.id
    first = decide(client, manager, expense_id, {"decision": "rejected", "comment": "Missing receipt"})
    second = decide(client, manager, expense_id, {"decision": "approved"})
    assert first.status_code == 200
    assert second.status_code == 409
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.rejected


def test_employee_cannot_decide(client, db_session, employee):
    expense = make_expense(db_session, employee.id)
    response = decide(client, employee, expense.id, {"decision": "approved"})
    assert response.status_code == 403
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.pending


def test_decision_without_token(client, db_session, employee):
    expense = make_expense(db_session, employee.id)
    response = client.post(
        f"/expenses/{expense.id}/decision", json={"decision": "approved"}
    )
    assert response.status_code == 401


def test_manager_cannot_decide_own_expense(client, db_session, manager):
    expense = make_expense(db_session, manager.id)
    response = decide(client, manager, expense.id, {"decision": "approved"})
    assert response.status_code == 403
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.pending


def test_manager_of_another_team_cannot_decide(client, db_session, employee, other_manager):
    expense = make_expense(db_session, employee.id)
    response = decide(client, other_manager, expense.id, {"decision": "approved"})
    assert response.status_code == 404
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.pending


def test_decide_missing_expense(client, manager):
    response = decide(client, manager, 999999, {"decision": "approved"})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "maybe"},
        {},
        {"decision": "rejected"},
        {"decision": "rejected", "comment": "   "},
        {"decision": "approved", "comment": "x" * 501},
    ],
    ids=[
        "unknown-decision",
        "missing-decision",
        "reject-without-comment",
        "reject-with-blank-comment",
        "comment-too-long",
    ],
)
def test_invalid_decision_is_rejected(client, db_session, manager, employee, body):
    expense = make_expense(db_session, employee.id)
    response = decide(client, manager, expense.id, body)
    assert response.status_code == 422
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.pending