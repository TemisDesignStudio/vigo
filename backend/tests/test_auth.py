from fastapi.testclient import TestClient

from main import app, sessions


def setup_function() -> None:
    sessions.clear()


def test_admin_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_logout_flow() -> None:
    client = TestClient(app)
    invalid = client.post("/api/auth/login", json={"username": "user", "password": "bad"})
    assert invalid.status_code == 401

    login = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json() == {"username": "user"}
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
