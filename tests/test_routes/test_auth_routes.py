def test_register_sets_session_cookie(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "New Patient", "email": "newpatient@example.com", "password": "Password123!", "role": "patient"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "patient"
    assert "access_token" in response.cookies


def test_register_duplicate_email_returns_409(client):
    payload = {"name": "Dup", "email": "dup@example.com", "password": "Password123!", "role": "patient"}
    assert client.post("/api/auth/register", json=payload).status_code == 200
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={"name": "Carl", "email": "carl@example.com", "password": "Password123!", "role": "patient"},
    )
    response = client.post("/api/auth/login", json={"email": "carl@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_patients_me_requires_authentication(client):
    response = client.get("/api/patients/me")
    assert response.status_code == 401
