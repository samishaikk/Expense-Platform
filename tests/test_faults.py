import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import faults


def fault_client():
    app = FastAPI()
    app.include_router(faults.router)
    return TestClient(app)

def test_fault_route_does_not_exist_by_default(client):
    response = client.get("/debug/fault")
    assert response.status_code == 404

def test_fault_without_options_succeeds():
    response = fault_client().get("/debug/fault")
    assert response.status_code == 200
    assert response.json() == {"delay_ms": 0, "fail": False}



def test_fail_option_returns_500():
    response = fault_client().get("/debug/fault?fail=true")
    assert response.status_code == 500
    assert response.json()["detail"] == "injected fault"

def test_delay_option_slows_the_response():
    start = time.perf_counter()
    response = fault_client().get("/debug/fault?delay_ms=200")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed >= 0.2
    
def test_delay_is_capped():
    response = fault_client().get("/debug/fault?delay_ms=6000")
    assert response.status_code == 422