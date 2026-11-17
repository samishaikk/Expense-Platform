import logging

from app.db import get_db
from app.main import app
from app.security import create_access_token

def test_unhandled_error_returns_clean_500_and_is_logged(client, caplog):
    class BrokenSession:
        def get(self, *args, **kwargs):
            raise RuntimeError("boom")

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    token = create_access_token(1)

    with caplog.at_level(logging.ERROR, logger="app.request"):
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    record = next(r for r in caplog.records if r.name == "app.request")
    assert record.status_code == 500
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None