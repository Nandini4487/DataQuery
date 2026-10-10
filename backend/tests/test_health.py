from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok_body(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_error_shape(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "message" in body
