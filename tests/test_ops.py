from prometheus_client import REGISTRY
from app.db import get_db
from app.main import app
from tests.factories import auth_header, make_expense


def count(route, status, method="GET"):
    value = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": method, "route": route, "status": str(status)},
    )
    return value or 0


def test_ready_when_database_is_up(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "up"


def test_ready_returns_503_while_health_stays_ok_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("database is down")

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200


def test_metrics_endpoint_uses_prometheus_format(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text


def test_route_template_is_the_label_not_the_raw_path(client, db_session, employee):
    expense = make_expense(db_session, employee.id)
    before = count("/expenses/{expense_id}", 200)
    client.get(f"/expenses/{expense.id}", headers=auth_header(employee))
    assert count("/expenses/{expense_id}", 200) == before + 1
    assert count(f"/expenses/{expense.id}", 200) == 0


def test_unknown_paths_share_one_label(client):
    before = count("unmatched", 404)
    client.get("/no-such-page-1")
    client.get("/no-such-page-2")
    assert count("unmatched", 404) == before + 2


def test_client_errors_are_counted_by_status(client):
    before = count("/auth/me", 401)
    client.get("/auth/me")
    assert count("/auth/me", 401) == before + 1


def test_metrics_endpoint_does_not_count_itself(client):
    client.get("/metrics")
    client.get("/metrics")
    assert count("/metrics", 200) == 0