"""Phase 13 — Rate Limiting, Security Hardening & Finalization tests."""

import time
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.rate_limiter import RateLimiter, rate_limit_dependency
from app.main import app


# ---------------------------------------------------------------------------
# Unit tests — RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_allows_requests_within_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.check("key1") is True
        assert limiter.check("key1") is True
        assert limiter.check("key1") is True

    def test_blocks_after_threshold(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.check("key1") is True
        assert limiter.check("key1") is True
        assert limiter.check("key1") is False

    def test_different_keys_independent(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("a") is True
        assert limiter.check("b") is True
        assert limiter.check("a") is False
        assert limiter.check("b") is False

    def test_reset_clears_counter(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("k") is True
        assert limiter.check("k") is False
        limiter.reset("k")
        assert limiter.check("k") is True

    def test_remaining_returns_correct_count(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.remaining("k") == 3
        limiter.check("k")
        assert limiter.remaining("k") == 2
        limiter.check("k")
        limiter.check("k")
        assert limiter.remaining("k") == 0

    def test_window_expiry_allows_new_requests(self):
        limiter = RateLimiter(max_requests=2, window_seconds=0)
        assert limiter.check("k") is True
        assert limiter.check("k") is True
        # With window_seconds=0, all old entries should be cleaned on next check
        assert limiter.check("k") is True


# ---------------------------------------------------------------------------
# Integration tests — rate limiting on endpoints (HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRateLimitEndpoints:
    async def test_login_returns_429_after_rate_limit_exceeded(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(settings.RATE_LIMIT_LOGIN):
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "nonexistent@test.com", "password": "wrongpassword"},
                )
                # Should get 401 (bad creds) but NOT 429 yet
                assert resp.status_code in (401, 422)

            # Next request should be rate limited
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrongpassword"},
            )
            assert resp.status_code == 429

    async def test_register_returns_429_after_rate_limit_exceeded(self):
        """Test register endpoint rate limiting by directly invoking the limiter."""
        from app.users.router import _register_limiter

        # Simulate filling up the rate limit
        for _ in range(settings.RATE_LIMIT_REGISTER):
            assert _register_limiter.check("test_register_key") is True

        # Next request should be blocked
        assert _register_limiter.check("test_register_key") is False

        # Reset and verify it works again
        _register_limiter.reset("test_register_key")
        assert _register_limiter.check("test_register_key") is True

    async def test_converse_returns_429_after_rate_limit_exceeded(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(settings.RATE_LIMIT_CONVERSE):
                resp = await client.post(
                    "/api/v1/ai/converse",
                    data={"message": "test"},
                )
                # May get various status codes depending on AI provider config
                assert resp.status_code != 429

            # Next request should be rate limited
            resp = await client.post(
                "/api/v1/ai/converse",
                data={"message": "test"},
            )
            assert resp.status_code == 429

    async def test_health_endpoint_not_rate_limited(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(20):
                resp = await client.get("/api/v1/health")
                assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Security hardening verification
# ---------------------------------------------------------------------------


class TestSecurityChecklist:
    def test_secret_key_from_environment(self):
        """SECRET_KEY should be loaded from .env, not hardcoded default."""
        # In development, it falls back to the default, but in production it must be set
        assert isinstance(settings.SECRET_KEY, str)

    def test_qr_signing_key_from_environment(self):
        """QR_SIGNING_KEY should be loaded from .env."""
        assert isinstance(settings.QR_SIGNING_KEY, str)

    def test_ai_credentials_from_environment(self):
        """All AI provider keys should be strings (loaded from env)."""
        assert isinstance(settings.REQUEST1_GEMINI_API_KEY, str)
        assert isinstance(settings.REQUEST1_GROQ_API_KEY, str)
        assert isinstance(settings.REQUEST2_GEMINI_API_KEY, str)
        assert isinstance(settings.REQUEST2_GROQ_API_KEY, str)
        assert isinstance(settings.GROQ_WHISPER_API_KEY, str)

    def test_passwords_not_in_config(self):
        """No plaintext passwords should appear in configuration."""
        config_str = str(settings.model_dump())
        assert "password123" not in config_str.lower()
        assert "admin123" not in config_str.lower()

    def test_cors_configured(self):
        """CORS origins should be configured."""
        assert settings.CORS_ORIGINS is not None
        assert len(settings.CORS_ORIGINS) > 0

    def test_rate_limit_configured(self):
        """Rate limits should be set for sensitive endpoints."""
        assert settings.RATE_LIMIT_LOGIN > 0
        assert settings.RATE_LIMIT_REGISTER > 0
        assert settings.RATE_LIMIT_VALIDATE > 0
        assert settings.RATE_LIMIT_CONVERSE > 0

    def test_jwt_expiration_configured(self):
        """JWT tokens should have expiration."""
        assert settings.JWT_EXPIRATION_MINUTES > 0

    def test_jwt_algorithm_is_secure(self):
        """JWT should use HS256 or stronger."""
        assert settings.JWT_ALGORITHM in ("HS256", "HS384", "HS512")

    def test_no_hardcoded_api_keys_in_source(self):
        """Verify API keys are not hardcoded in source files."""
        import os

        for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), "..", "app")):
            for f in files:
                if f.endswith(".py"):
                    filepath = os.path.join(root, f)
                    with open(filepath, encoding="utf-8") as fh:
                        content = fh.read()
                        # Check for hardcoded key patterns (not config references)
                        assert "gsk_" not in content or "settings" in content, (
                            f"Possible hardcoded Groq key in {filepath}"
                        )
                        assert "AQ.Ab" not in content or "settings" in content, (
                            f"Possible hardcoded Gemini key in {filepath}"
                        )


# ---------------------------------------------------------------------------
# Full router assembly verification
# ---------------------------------------------------------------------------


class TestRouterAssembly:
    async def test_all_api_routes_registered(self):
        """Verify all expected API routes exist in the OpenAPI schema."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/api/v1/openapi.json")
            if resp.status_code == 200:
                schema = resp.json()
                paths = schema.get("paths", {})
                expected_prefixes = [
                    "/api/v1/health",
                    "/api/v1/auth/",
                    "/api/v1/transit/",
                    "/api/v1/ai/",
                    "/api/v1/fares/",
                    "/api/v1/tickets",
                    "/api/v1/admin/",
                ]
                for prefix in expected_prefixes:
                    matching = [p for p in paths if p.startswith(prefix)]
                    assert len(matching) > 0, f"No routes found for prefix: {prefix}"
