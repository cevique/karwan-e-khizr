import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Reset all in-memory rate limiters before every test.

    The rate limiters used by the auth/ticketing/AI endpoints are simple
    in-memory singletons keyed by client IP. FastAPI's TestClient always
    uses the same client IP, so without this reset, tests that hit a
    rate-limited endpoint several times across the suite trip the limiter
    and cause unrelated-looking failures later on (typically 429s where a
    200 was expected). This does not affect production behaviour - it only
    runs under pytest.
    """
    from app.users.router import _login_limiter, _register_limiter
    from app.ticketing.router import _validate_limiter
    from app.api.ai_router import _converse_limiter

    limiters = (_login_limiter, _register_limiter, _validate_limiter, _converse_limiter)
    for limiter in limiters:
        limiter.reset_all()

    yield

    for limiter in limiters:
        limiter.reset_all()


@pytest.fixture(autouse=True)
async def _rebind_db_engine_to_event_loop():
    """Rebind the global async DB engine to the current test's event loop.

    ``app.core.database.engine`` is created once at module import time and
    its asyncpg connections are lazily bound to whichever event loop is
    active when they're first used. pytest-asyncio gives each test function
    its own event loop, so a connection created during one test file is
    invalid by the time a later test (in a different file, running in a new
    loop) tries to reuse it - it fails with "RuntimeError: Event loop is
    closed".

    Most test files already guard against this themselves via a
    file-local ``db_session`` fixture that calls ``init_db()``, which
    disposes the pool (without closing it) and lets it lazily recreate
    connections bound to the current loop. Test files/tests that talk to
    the app (e.g. via TestClient/AsyncClient) without going through such a
    fixture don't get that protection. Calling the cheap, idempotent
    ``init_db()`` here for every test closes that gap suite-wide, whether
    or not a given test also has its own ``db_session`` fixture.
    """
    from app.core.database import init_db

    await init_db()
    yield
