import time
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, AsyncSessionLocal, close_db
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.db.models.user import User
from app.main import create_app
from app.users.service import UserService


@pytest.fixture(scope="function")
async def db_session():
    await init_db()
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM users"))
        await session.commit()
        yield session
    await close_db()


@pytest.fixture(scope="function")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "securepass"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_verify_wrong_password(self):
        password = "securepass"
        hashed = hash_password(password)
        assert not verify_password("wrongpass", hashed)

    def test_different_hashes_for_same_password(self):
        password = "securepass"
        h1 = hash_password(password)
        h2 = hash_password(password)
        assert h1 != h2
        assert verify_password(password, h1)
        assert verify_password(password, h2)


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token(subject="1", role="passenger")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["role"] == "passenger"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_tampered_token(self):
        token = create_access_token(subject="1", role="passenger")
        tampered = token[:-5] + "XXXXX"
        payload = decode_token(tampered)
        assert payload is None

    def test_token_has_expiry(self):
        token = create_access_token(subject="1", role="passenger")
        payload = decode_token(token)
        assert payload["exp"] > time.time()

    def test_token_with_custom_expiry(self):
        expires_delta = timedelta(minutes=60)
        token = create_access_token(subject="1", role="passenger", expires_delta=expires_delta)
        payload = decode_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = (exp_time - now).total_seconds()
        assert 3500 < diff < 3700

    def test_expired_token_rejected(self):
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(subject="1", role="passenger", expires_delta=expires_delta)
        payload = decode_token(token)
        assert payload is None


class TestUserService:
    @pytest.mark.asyncio
    async def test_register_creates_user(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="test@example.com", password="pass123")
        assert user.email == "test@example.com"
        assert user.role == "passenger"
        assert user.is_active is True
        assert user.hashed_password != "pass123"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises(self, db_session: AsyncSession):
        service = UserService(db_session)
        await service.register(email="dup@example.com", password="pass123")
        with pytest.raises(Exception) as exc_info:
            await service.register(email="dup@example.com", password="pass456")
        assert "already registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_success(self, db_session: AsyncSession):
        service = UserService(db_session)
        await service.register(email="login@example.com", password="pass123")
        token, user = await service.login(email="login@example.com", password="pass123")
        assert token is not None
        assert user.email == "login@example.com"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, db_session: AsyncSession):
        service = UserService(db_session)
        await service.register(email="wrong@example.com", password="pass123")
        with pytest.raises(Exception) as exc_info:
            await service.login(email="wrong@example.com", password="wrongpass")
        assert "Invalid email or password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, db_session: AsyncSession):
        service = UserService(db_session)
        with pytest.raises(Exception) as exc_info:
            await service.login(email="nonexistent@example.com", password="pass123")
        assert "Invalid email or password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="find@example.com", password="pass123")
        found = await service.get_by_id(user.id)
        assert found.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        service = UserService(db_session)
        with pytest.raises(Exception) as exc_info:
            await service.get_by_id(99999)
        assert "not found" in str(exc_info.value).lower()


class TestAuthAPI:
    def test_register_success(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={
            "email": "api@example.com",
            "password": "pass123",
            "full_name": "Test User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "api@example.com"
        assert data["role"] == "passenger"
        assert "id" in data

    def test_register_duplicate_email(self, client: TestClient):
        client.post("/api/v1/auth/register", json={
            "email": "dup_api@example.com",
            "password": "pass123",
        })
        response = client.post("/api/v1/auth/register", json={
            "email": "dup_api@example.com",
            "password": "pass456",
        })
        assert response.status_code == 409

    def test_register_invalid_email(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "pass123",
        })
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "password": "12345",
        })
        assert response.status_code == 422

    def test_login_success(self, client: TestClient):
        client.post("/api/v1/auth/register", json={
            "email": "login_api@example.com",
            "password": "pass123",
        })
        response = client.post("/api/v1/auth/login", json={
            "email": "login_api@example.com",
            "password": "pass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login_api@example.com"
        assert data["user"]["role"] == "passenger"

    def test_login_wrong_password(self, client: TestClient):
        client.post("/api/v1/auth/register", json={
            "email": "wrong_api@example.com",
            "password": "pass123",
        })
        response = client.post("/api/v1/auth/login", json={
            "email": "wrong_api@example.com",
            "password": "wrongpass",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "pass123",
        })
        assert response.status_code == 401

    def test_get_me_with_token(self, client: TestClient):
        reg_resp = client.post("/api/v1/auth/register", json={
            "email": "me_api@example.com",
            "password": "pass123",
            "full_name": "Me User",
        })
        assert reg_resp.status_code == 201
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "me_api@example.com",
            "password": "pass123",
        })
        token = login_resp.json()["access_token"]
        me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["email"] == "me_api@example.com"
        assert data["full_name"] == "Me User"
        assert data["role"] == "passenger"

    def test_get_me_without_token(self, client: TestClient):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_with_invalid_token(self, client: TestClient):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == 401

    def test_get_me_with_expired_token(self, client: TestClient):
        client.post("/api/v1/auth/register", json={
            "email": "expired_api@example.com",
            "password": "pass123",
        })
        expired_token = create_access_token(
            subject="1",
            role="passenger",
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401


class TestRoleAuthorization:
    @pytest.mark.asyncio
    async def test_require_admin_rejects_passenger(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="passenger@example.com", password="pass123")
        assert user.role == "passenger"
        with pytest.raises(Exception) as exc_info:
            from app.users.dependencies import require_admin
            await require_admin(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_accepts_admin(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="admin_check@example.com", password="pass123")
        user.role = "admin"
        await db_session.commit()
        from app.users.dependencies import require_admin
        result = await require_admin(user)
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_require_role_rejects_wrong_role(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="role_test@example.com", password="pass123")
        from app.users.dependencies import require_role
        admin_dep = require_role("admin")
        with pytest.raises(Exception) as exc_info:
            admin_dep(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_role_accepts_correct_role(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="role_ok@example.com", password="pass123")
        from app.users.dependencies import require_role
        passenger_dep = require_role("passenger")
        result = passenger_dep(user)
        assert result.role == "passenger"


class TestSecurityEdgeCases:
    def test_sql_injection_in_email_rejected(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={
            "email": "'; DROP TABLE users; --",
            "password": "pass123",
        })
        assert response.status_code == 422

    def test_empty_email_rejected(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={
            "email": "",
            "password": "pass123",
        })
        assert response.status_code == 422

    def test_missing_fields_rejected(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422

    def test_login_with_empty_body(self, client: TestClient):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_password_not_returned_in_responses(self, client: TestClient):
        reg_resp = client.post("/api/v1/auth/register", json={
            "email": "no_pass@example.com",
            "password": "pass123",
        })
        data = reg_resp.json()
        assert "password" not in data
        assert "hashed_password" not in data

    def test_login_response_no_password(self, client: TestClient):
        client.post("/api/v1/auth/register", json={
            "email": "login_nopass@example.com",
            "password": "pass123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "login_nopass@example.com",
            "password": "pass123",
        })
        data = resp.json()
        assert "password" not in data
        assert "hashed_password" not in data


class TestUserModel:
    @pytest.mark.asyncio
    async def test_user_role_default_is_passenger(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="default_role@example.com", password="pass123")
        assert user.role == "passenger"

    @pytest.mark.asyncio
    async def test_user_is_active_by_default(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="active@example.com", password="pass123")
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_user_email_unique(self, db_session: AsyncSession):
        service = UserService(db_session)
        await service.register(email="unique@example.com", password="pass123")
        with pytest.raises(Exception):
            await service.register(email="unique@example.com", password="pass456")

    @pytest.mark.asyncio
    async def test_user_full_name_optional(self, db_session: AsyncSession):
        service = UserService(db_session)
        user = await service.register(email="noname@example.com", password="pass123")
        assert user.full_name is None


class TestAuthFlow:
    def test_full_register_login_me_flow(self, client: TestClient):
        register_resp = client.post("/api/v1/auth/register", json={
            "email": "flow@example.com",
            "password": "securepass",
            "full_name": "Flow User",
        })
        assert register_resp.status_code == 201
        user_id = register_resp.json()["id"]

        login_resp = client.post("/api/v1/auth/login", json={
            "email": "flow@example.com",
            "password": "securepass",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        assert login_resp.json()["user"]["id"] == user_id

        me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["id"] == user_id
        assert me_resp.json()["email"] == "flow@example.com"
        assert me_resp.json()["full_name"] == "Flow User"
        assert me_resp.json()["role"] == "passenger"

    def test_register_with_optional_name(self, client: TestClient):
        resp = client.post("/api/v1/auth/register", json={
            "email": "noname_flow@example.com",
            "password": "pass123",
        })
        assert resp.status_code == 201
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "noname_flow@example.com",
            "password": "pass123",
        })
        token = login_resp.json()["access_token"]
        me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.json()["full_name"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
