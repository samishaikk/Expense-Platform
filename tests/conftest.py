import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://expense_user:expense_pass@localhost:5433/expense_test_db",
)
assert "test" in TEST_DATABASE_URL, "Refusing to run tests against a non-test database"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  
from fastapi.testclient import TestClient  
from sqlalchemy.orm import Session  
from app.db import Base, engine, get_db  
from app.main import app  
from app.models import Role  
from tests.factories import make_employee  


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
    )
    yield session
    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def manager(db_session):
    return make_employee(db_session, "manager@example.com", role=Role.manager, name="Sami Manager")


@pytest.fixture
def employee(db_session, manager):
    return make_employee(db_session, "employee@example.com", manager_id=manager.id, name="Ravi Employee")

@pytest.fixture
def other_manager(db_session):
    return make_employee(db_session, "other.manager@example.com", role=Role.manager, name="Omar Manager")


@pytest.fixture
def other_employee(db_session, other_manager):
    return make_employee(db_session, "other.employee@example.com", manager_id=other_manager.id, name="Olga Employee")