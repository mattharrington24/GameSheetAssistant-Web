import os

os.environ.setdefault("APP_PASSWORD", "test-password")
os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module


def test_health_is_public():
    client = app_module.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_index_requires_login():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.location


def test_login_allows_index():
    client = app_module.app.test_client()
    response = client.post("/login", data={"password": "test-password"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"GameSheet Assistant" in response.data
