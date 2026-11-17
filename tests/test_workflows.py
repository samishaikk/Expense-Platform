from tests.factories import auth_header


def login_headers(client, email, password):
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_full_expense_lifecycle(client, manager):
    manager_headers = auth_header(manager)

    created = client.post(
        "/employees",
        json={
            "name": "Nina New",
            "email": "nina@example.com",
            "password": "password123",
            "role": "employee",
            "manager_id": manager.id,
        },
        headers=manager_headers,
    )
    assert created.status_code == 201

    employee_headers = login_headers(client, "nina@example.com", "password123")

    submitted = client.post(
        "/expenses",
        json={"amount": "250.00", "category": "meals", "description": "Client dinner"},
        headers=employee_headers,
    )
    assert submitted.status_code == 201
    expense_id = submitted.json()["id"]
    assert submitted.json()["status"] == "pending"

    team = client.get("/expenses/team?status=pending", headers=manager_headers)
    assert expense_id in [item["id"] for item in team.json()]

    decision = client.post(
        f"/expenses/{expense_id}/decision",
        json={"decision": "approved", "comment": "Within policy"},
        headers=manager_headers,
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    mine = client.get(f"/expenses/{expense_id}", headers=employee_headers)
    assert mine.json()["status"] == "approved"

    history = client.get(f"/expenses/{expense_id}/history", headers=employee_headers)
    rows = history.json()
    assert [row["action"] for row in rows] == ["submitted", "approved"]
    assert rows[1]["comment"] == "Within policy"

    still_pending = client.get("/expenses/team?status=pending", headers=manager_headers)
    assert expense_id not in [item["id"] for item in still_pending.json()]

    again = client.post(
        f"/expenses/{expense_id}/decision",
        json={"decision": "approved"},
        headers=manager_headers,
    )
    assert again.status_code == 409


def test_rejection_lifecycle(client, manager, employee):
    employee_headers = auth_header(employee)
    manager_headers = auth_header(manager)

    expense_id = client.post(
        "/expenses",
        json={"amount": "80.00", "category": "software", "description": "Plugin license"},
        headers=employee_headers,
    ).json()["id"]

    rejection = client.post(
        f"/expenses/{expense_id}/decision",
        json={"decision": "rejected", "comment": "Not on the approved list"},
        headers=manager_headers,
    )
    assert rejection.status_code == 200

    mine = client.get("/expenses?status=rejected", headers=employee_headers)
    assert [item["id"] for item in mine.json()] == [expense_id]

    history = client.get(f"/expenses/{expense_id}/history", headers=employee_headers).json()
    assert [row["action"] for row in history] == ["submitted", "rejected"]
    assert history[1]["comment"] == "Not on the approved list"