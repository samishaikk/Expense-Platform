import json
import logging

from app.logging_config import JsonFormatter
from tests.factories import TEST_PASSWORD, auth_header


def test_formatter_outputs_valid_json_with_extra_fields():
    record = logging.LogRecord(
        name="demo", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    record.request_id = "abc123"
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == "hello"
    assert entry["level"] == "INFO"
    assert entry["request_id"] == "abc123"
    assert "timestamp" in entry


def test_request_log_has_expected_fields(client, employee, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/auth/me", headers=auth_header(employee))
    record = next(r for r in caplog.records if r.name == "app.request")
    assert record.method == "GET"
    assert record.path == "/auth/me"
    assert record.status_code == 200
    assert record.user_id == employee.id
    assert record.user_role == "employee"
    assert record.latency_ms >= 0
    assert record.request_id == response.headers["X-Request-ID"]


def test_client_errors_are_logged_as_warnings(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/auth/me")
    record = next(r for r in caplog.records if r.name == "app.request")
    assert record.status_code == 401
    assert record.levelno == logging.WARNING
    assert record.user_id is None


def test_passwords_and_tokens_never_reach_the_logs(client, employee, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        login = client.post(
            "/auth/login",
            data={"username": employee.email, "password": TEST_PASSWORD},
        )
        token = login.json()["access_token"]
        client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    everything = " ".join(str(record.__dict__) for record in caplog.records)
    assert TEST_PASSWORD not in everything
    assert token not in everything