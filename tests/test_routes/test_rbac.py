def register(client, role, email):
    return client.post(
        "/api/auth/register",
        json={"name": role.title(), "email": email, "password": "Password123!", "role": role},
    )


def test_patient_cannot_access_staff_routes(client):
    register(client, "patient", "patient-rbac@example.com")
    response = client.get("/api/staff/workflows")
    assert response.status_code == 403


def test_staff_cannot_access_patient_only_routes(client):
    register(client, "staff", "staff-rbac@example.com")
    response = client.get("/api/patients/me")
    assert response.status_code == 403


def test_staff_can_access_staff_routes(client):
    register(client, "staff", "staff-ok@example.com")
    response = client.get("/api/staff/workflows")
    assert response.status_code == 200
    assert response.json() == []


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/staff/workflows").status_code == 401
    assert client.get("/api/appointments").status_code == 401
