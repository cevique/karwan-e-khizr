import pytest

from app.core.config import Settings, validate_required_settings
from app.core.constants import (
    AVERAGE_WALKING_SPEED_MPS,
    CURRENCY,
    DEFAULT_BASE_FARE,
    DEFAULT_WALKING_RADIUS_M,
    MAX_WALKING_RADIUS_M,
)
from app.core.exceptions import (
    AmbiguousLocationError,
    AppException,
    ConflictError,
    ForbiddenError,
    NoRouteFoundError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.security import create_access_token, decode_token, hash_password, verify_password


class TestConfig:
    def test_settings_load_from_env(self):
        settings = Settings(_env_file=".env")
        assert settings.DATABASE_URL == "postgresql+asyncpg://postgres:postgres@localhost:5432/karwan"
        assert settings.APP_ENV == "development"
        assert settings.LOG_LEVEL == "INFO"

    def test_required_settings_validation_passes_in_development(self):
        # Should not raise in development mode even with missing keys
        Settings(APP_ENV="development")
        validate_required_settings()  # Should not raise

    def test_required_settings_validation_fails_in_production(self):
        # Need to patch the global settings
        import app.core.config as config_module
        original_settings = config_module.settings
        config_module.settings = Settings(APP_ENV="production", SECRET_KEY="", QR_SIGNING_KEY="")
        try:
            with pytest.raises(ValueError, match="Missing required configuration"):
                validate_required_settings()
        finally:
            config_module.settings = original_settings


class TestConstants:
    def test_walking_radius_defaults(self):
        assert DEFAULT_WALKING_RADIUS_M == 400.0
        assert MAX_WALKING_RADIUS_M == 2000.0

    def test_walking_speed(self):
        assert AVERAGE_WALKING_SPEED_MPS == 1.4

    def test_currency(self):
        assert CURRENCY == "PKR"

    def test_default_fares(self):
        assert DEFAULT_BASE_FARE == 50.0


class TestExceptions:
    def test_app_exception_base(self):
        exc = AppException("Test message", code="TEST_CODE", status_code=400)
        assert exc.message == "Test message"
        assert exc.code == "TEST_CODE"
        assert exc.status_code == 400
        assert exc.details == {}

    def test_app_exception_with_details(self):
        exc = AppException("Test", details={"key": "value"})
        assert exc.details == {"key": "value"}

    def test_validation_error(self):
        exc = ValidationError("Invalid input")
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == 400

    def test_not_found_error(self):
        exc = NotFoundError("Not found")
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404

    def test_unauthorized_error(self):
        exc = UnauthorizedError()
        assert exc.code == "UNAUTHORIZED"
        assert exc.status_code == 401
        assert exc.message == "Unauthorized"

    def test_forbidden_error(self):
        exc = ForbiddenError()
        assert exc.code == "FORBIDDEN"
        assert exc.status_code == 403

    def test_conflict_error(self):
        exc = ConflictError("Conflict")
        assert exc.code == "CONFLICT"
        assert exc.status_code == 409

    def test_ambiguous_location_error(self):
        candidates = [{"name": "A"}, {"name": "B"}]
        exc = AmbiguousLocationError(candidates)
        assert exc.code == "AMBIGUOUS_LOCATION"
        assert exc.status_code == 400
        assert exc.details["candidates"] == candidates

    def test_no_route_found_error(self):
        exc = NoRouteFoundError()
        assert exc.code == "NO_ROUTE_FOUND"
        assert exc.status_code == 404


class TestSecurity:
    def test_hash_and_verify_password(self):
        password = "securepass"  # bcrypt has 72 byte limit
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpass", hashed)

    def test_create_and_decode_token(self):
        token = create_access_token(subject="1", role="passenger")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["role"] == "passenger"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_token_expiration(self):
        import time
        token = create_access_token(subject="1", role="passenger", expires_delta=None)
        payload = decode_token(token)
        assert payload["exp"] > time.time()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])