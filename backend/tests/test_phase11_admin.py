import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, AsyncSessionLocal, close_db
from app.core.security import create_access_token
from app.db.models.user import User
from app.main import create_app


@pytest.fixture(scope="function")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _register_user(client: TestClient, email: str, password: str = "pass123"):
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def _promote_user(user_id: int):
    import asyncio
    import asyncpg

    async def _do():
        conn = await asyncpg.connect(
            host="localhost", port=5432, user="postgres",
            password="postgres", database="karwan"
        )
        await conn.execute(
            "UPDATE users SET role = 'admin' WHERE id = $1", user_id
        )
        await conn.close()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()


def _login(client: TestClient, email: str, password: str = "pass123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _unique_email(prefix: str = "admin") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client: TestClient):
    email = _unique_email("admin")
    user_id = _register_user(client, email)
    _promote_user(user_id)
    return _login(client, email)


@pytest.fixture
def passenger_token(client: TestClient):
    email = _unique_email("passenger")
    _register_user(client, email)
    return _login(client, email)


class TestAdminAuthorization:
    def test_no_token_returns_401(self, client: TestClient):
        response = client.get("/api/v1/admin/data/status")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient):
        response = client.get(
            "/api/v1/admin/data/status",
            headers=auth_header("invalidtoken"),
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient):
        expired_token = create_access_token(
            subject="1",
            role="admin",
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get(
            "/api/v1/admin/data/status",
            headers=auth_header(expired_token),
        )
        assert response.status_code == 401

    def test_passenger_returns_403(self, client: TestClient, passenger_token: str):
        response = client.get(
            "/api/v1/admin/data/status",
            headers=auth_header(passenger_token),
        )
        assert response.status_code == 403

    def test_admin_returns_200(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/data/status",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200


class TestAdminDataStatus:
    def test_data_status_schema(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/data/status",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "stops" in data
        assert "routes" in data
        assert "agencies" in data
        assert "total" in data["stops"]
        assert "with_coordinates" in data["stops"]
        assert "without_coordinates" in data["stops"]
        assert "total" in data["routes"]
        assert "with_geometry" in data["routes"]
        assert "without_geometry" in data["routes"]
        assert "with_timetable" in data["routes"]
        assert "without_timetable" in data["routes"]
        assert "total" in data["agencies"]

    def test_data_status_counts_are_integers(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/data/status",
            headers=auth_header(admin_token),
        )
        data = response.json()
        assert isinstance(data["stops"]["total"], int)
        assert isinstance(data["routes"]["total"], int)
        assert isinstance(data["agencies"]["total"], int)


class TestAdminSimulationStatus:
    def test_simulation_status_schema(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/simulation/status",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "active_vehicles" in data
        assert "active_trips" in data
        assert isinstance(data["running"], bool)
        assert isinstance(data["active_vehicles"], int)
        assert isinstance(data["active_trips"], int)

    def test_simulation_not_running_initially(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/simulation/status",
            headers=auth_header(admin_token),
        )
        data = response.json()
        assert data["running"] is False
        assert data["active_vehicles"] == 0
        assert data["active_trips"] == 0
        assert data["simulation_time"] is None


class TestAdminTickets:
    def test_tickets_list_schema(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/tickets",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)

    def test_tickets_list_returns_list(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/tickets",
            headers=auth_header(admin_token),
        )
        data = response.json()
        assert isinstance(data["tickets"], list)
        assert len(data["tickets"]) >= 0

    def test_ticket_not_found_returns_404(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/v1/admin/tickets/99999",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 404


class TestAdminSeedRun:
    def test_seed_requires_admin(self, client: TestClient):
        response = client.post("/api/v1/admin/seed/run")
        assert response.status_code == 401

    def test_seed_passenger_forbidden(self, client: TestClient, passenger_token: str):
        response = client.post(
            "/api/v1/admin/seed/run",
            headers=auth_header(passenger_token),
        )
        assert response.status_code == 403

    def test_seed_admin_returns_200(self, client: TestClient, admin_token: str):
        response = client.post(
            "/api/v1/admin/seed/run",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "imported" in data
        assert data["status"] == "completed"


class TestAdminSimulationStartStop:
    def test_start_simulation_requires_admin(self, client: TestClient):
        response = client.post("/api/v1/admin/simulation/start")
        assert response.status_code == 401

    def test_start_simulation_passenger_forbidden(self, client: TestClient, passenger_token: str):
        response = client.post(
            "/api/v1/admin/simulation/start",
            headers=auth_header(passenger_token),
        )
        assert response.status_code == 403

    def test_stop_simulation_requires_admin(self, client: TestClient):
        response = client.post("/api/v1/admin/simulation/stop")
        assert response.status_code == 401

    def test_stop_simulation_passenger_forbidden(self, client: TestClient, passenger_token: str):
        response = client.post(
            "/api/v1/admin/simulation/stop",
            headers=auth_header(passenger_token),
        )
        assert response.status_code == 403

    def test_start_stop_simulation_admin_returns_200(self, client: TestClient, admin_token: str):
        start_resp = client.post(
            "/api/v1/admin/simulation/start",
            headers=auth_header(admin_token),
        )
        assert start_resp.status_code == 200
        start_data = start_resp.json()
        assert start_data["status"] == "started"

        stop_resp = client.post(
            "/api/v1/admin/simulation/stop",
            headers=auth_header(admin_token),
        )
        assert stop_resp.status_code == 200
        stop_data = stop_resp.json()
        assert stop_data["status"] == "stopped"


class TestAdminEndpointCompleteness:
    def test_all_admin_endpoints_require_auth(self, client: TestClient):
        endpoints = [
            ("GET", "/api/v1/admin/data/status"),
            ("GET", "/api/v1/admin/simulation/status"),
            ("GET", "/api/v1/admin/tickets"),
            ("GET", "/api/v1/admin/tickets/1"),
            ("POST", "/api/v1/admin/seed/run"),
            ("POST", "/api/v1/admin/simulation/start"),
            ("POST", "/api/v1/admin/simulation/stop"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path)
            assert response.status_code == 401, f"{method} {path} should require auth"

    def test_all_admin_endpoints_reject_passenger(self, client: TestClient, passenger_token: str):
        headers = auth_header(passenger_token)
        endpoints = [
            ("GET", "/api/v1/admin/data/status"),
            ("GET", "/api/v1/admin/simulation/status"),
            ("GET", "/api/v1/admin/tickets"),
            ("GET", "/api/v1/admin/tickets/1"),
            ("POST", "/api/v1/admin/seed/run"),
            ("POST", "/api/v1/admin/simulation/start"),
            ("POST", "/api/v1/admin/simulation/stop"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path, headers=headers)
            else:
                response = client.post(path, headers=headers)
            assert response.status_code == 403, f"{method} {path} should reject passenger"


class TestHealthEndpoints:
    def test_health_endpoint(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_db_endpoint(self, client: TestClient):
        response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data

    def test_ai_health_endpoint(self, client: TestClient):
        response = client.get("/api/v1/ai/health")
        assert response.status_code == 200
        data = response.json()
        assert "speech_to_text" in data
        assert "intent_llm" in data
        assert "response_llm" in data
        assert "status" in data["speech_to_text"]
        assert "status" in data["intent_llm"]
        assert "status" in data["response_llm"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
