from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.auth.service import (
    AuthUser,
    create_pending_2fa_token,
    create_session_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_pending_2fa_token,
    verify_session_token,
    verify_totp,
)
from app.db.base import Base
from app.users.models import User

SECRET_PATTERN = re.compile(r'name="secret" value="([A-Z2-7]{16,32})"')


def _get_user(user: User) -> User:
    """Detach user from its session so it can be refreshed in another."""
    # Return the id for re-fetching
    return user


def test_auth_user_dataclass() -> None:
    user = AuthUser(user_id="abc-123", email="test@example.com")
    assert user.user_id == "abc-123"
    assert user.email == "test@example.com"


def test_hash_and_verify_password() -> None:
    h = hash_password("mypassword")
    assert h != "mypassword"
    assert verify_password("mypassword", h)
    assert not verify_password("wrongpassword", h)


def test_create_and_verify_session_token() -> None:
    token = create_session_token("user-42", "a@b.com")
    user = verify_session_token(token)
    assert user is not None
    assert user.user_id == "user-42"
    assert user.email == "a@b.com"
    assert verify_session_token("not.a.valid.token") is None


def test_create_and_verify_pending_2fa_token() -> None:
    token = create_pending_2fa_token("user-99")
    assert verify_pending_2fa_token(token) == "user-99"
    assert verify_pending_2fa_token("bad.token.here") is None


def test_pending_2fa_token_rejected_by_session_verifier() -> None:
    token = create_pending_2fa_token("user-55")
    assert verify_session_token(token) is None


def test_generate_totp_secret() -> None:
    secret = generate_totp_secret()
    assert len(secret) == 32
    totp = pyotp.TOTP(secret, interval=30, digits=6)
    code = totp.now()
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000000")


@pytest.fixture
async def db_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.auth import routes as auth_routes
    from app.db import engine as db_engine

    orig_routes_factory = auth_routes._get_session_factory
    orig_engine_factory = db_engine._get_session_factory
    orig_engine = db_engine._engine
    orig_session = db_engine._session_factory

    auth_routes._get_session_factory = lambda: factory
    db_engine._get_session_factory = lambda: factory
    db_engine._engine = None  # type: ignore[assignment]
    db_engine._session_factory = None  # type: ignore[assignment]

    yield factory

    auth_routes._get_session_factory = orig_routes_factory
    db_engine._get_session_factory = orig_engine_factory
    db_engine._engine = orig_engine
    db_engine._session_factory = orig_session
    await engine.dispose()


async def _create_user(
    factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "user@test.dev",
    password: str = "Supersecret1",
    role: str = "admin",
    totp_secret: str | None = None,
) -> User:
    async with factory() as db:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _fetch_user(
    factory: async_sessionmaker[AsyncSession], user_id: uuid.UUID
) -> User:
    async with factory() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()


# --- Login flows ---


async def test_login_with_real_db(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create_user(db_factory)
    response = await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert client.cookies.get("nesti_session")


async def test_login_wrong_password(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create_user(db_factory)
    response = await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "wrong"}
    )
    assert response.status_code == 303
    assert "invalid_credentials" in response.headers["location"]
    assert not client.cookies.get("nesti_session")


async def test_login_2fa_two_steps(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    secret = "JBSWY3DPEHPK3PXP"
    await _create_user(db_factory, totp_secret=secret)
    totp = pyotp.TOTP(secret, interval=30, digits=6)

    response = await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"
    assert client.cookies.get("nesti_pending_2fa")
    assert not client.cookies.get("nesti_session")

    response = await client.post("/auth/login/2fa", data={"code": "000000"})
    assert response.status_code == 303
    assert "invalid_code" in response.headers["location"]
    assert not client.cookies.get("nesti_session")

    response = await client.post("/auth/login/2fa", data={"code": totp.now()})
    assert response.status_code == 303
    assert client.cookies.get("nesti_session")
    assert not client.cookies.get("nesti_pending_2fa")


# --- Anti-bruteforce ---


async def test_account_lockout_after_max_attempts(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    from app.config import get_settings

    user = await _create_user(db_factory)
    max_attempts = get_settings().login_max_attempts

    for _ in range(max_attempts):
        await client.post(
            "/auth/login",
            data={"email": "user@test.dev", "password": "wrong"},
        )

    db_user = await _fetch_user(db_factory, user.id)
    assert db_user.locked_until is not None

    response = await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )
    assert "account_locked" in response.headers["location"]


async def test_successful_login_resets_attempts(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await _create_user(db_factory)

    await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "wrong"}
    )
    await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "wrong"}
    )

    await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )

    db_user = await _fetch_user(db_factory, user.id)
    assert db_user.failed_login_attempts == 0
    assert db_user.locked_until is None


async def test_wrong_totp_counts_as_failed_login(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await _create_user(db_factory, totp_secret="JBSWY3DPEHPK3PXP")

    await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )
    await client.post("/auth/login/2fa", data={"code": "000000"})

    db_user = await _fetch_user(db_factory, user.id)
    assert db_user.failed_login_attempts == 1


# --- 2FA setup ---


async def test_enable_2fa_flow(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await _create_user(db_factory)
    assert user.totp_secret is None

    response = await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )
    assert response.status_code == 303

    setup = await client.get("/profile/2fa")
    assert setup.status_code == 200
    match = SECRET_PATTERN.search(setup.text)
    assert match is not None
    secret = match.group(1)

    bad = await client.post(
        "/profile/2fa/confirm", data={"code": "000000", "secret": secret}
    )
    assert bad.status_code == 200
    db_user = await _fetch_user(db_factory, user.id)
    assert db_user.totp_secret is None

    totp = pyotp.TOTP(secret, interval=30, digits=6)
    ok = await client.post(
        "/profile/2fa/confirm", data={"code": totp.now(), "secret": secret}
    )
    assert ok.status_code == 303
    db_user = await _fetch_user(db_factory, user.id)
    assert db_user.totp_secret == secret


async def test_disable_2fa_self(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    secret = "JBSWY3DPEHPK3PXP"
    user = await _create_user(db_factory, totp_secret=secret)
    totp = pyotp.TOTP(secret, interval=30, digits=6)

    await client.post(
        "/auth/login", data={"email": "user@test.dev", "password": "Supersecret1"}
    )
    await client.post("/auth/login/2fa", data={"code": totp.now()})
    assert client.cookies.get("nesti_session")

    await client.post("/profile/2fa/disable")
    db_user = await _fetch_user(db_factory, user.id)
    assert db_user.totp_secret is None


# --- Profile / Pages ---


async def test_profile_view(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create_user(db_factory, email="viewer@test.dev", role="viewer")
    await client.post(
        "/auth/login", data={"email": "viewer@test.dev", "password": "Supersecret1"}
    )
    profile = await client.get("/profile")
    assert profile.status_code == 200
    assert "viewer@test.dev" in profile.text


async def test_login_page_renders(client: AsyncClient) -> None:
    response = await client.get("/auth/login")
    assert response.status_code == 200


async def test_logout_redirects(client: AsyncClient) -> None:
    response = await client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


async def test_protected_route_without_auth(client: AsyncClient) -> None:
    response = await client.get("/admin/users", follow_redirects=False)
    assert response.status_code in (303, 401, 403)
