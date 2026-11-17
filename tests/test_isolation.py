from app.models import Employee
from tests.factories import make_employee


def test_a_creates_a_row(db_session):
    make_employee(db_session, "isolation@example.com")
    count = db_session.query(Employee).filter_by(email="isolation@example.com").count()
    assert count == 1


def test_b_row_from_a_is_gone(db_session):
    count = db_session.query(Employee).filter_by(email="isolation@example.com").count()
    assert count == 0