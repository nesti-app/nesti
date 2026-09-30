"""Regression tests for the three security fixes.

1. SECRET_KEY must never be empty/placeholder — a predictable HS256 key lets
   anyone forge a session cookie (full auth + 2FA bypass).
2. The /access autocomplete JSON endpoints expose every user email and item
   name, so they must require an admin session.
3. serve_image_file hands out raw bytes and must honour the access-scope model.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.access.models import (
    AccessScope,
    AccessScopePermission,
    AccessScopeRule,
)
from app.auth.service import COOKIE_SESSION, hash_password
from app.config import MIN_SECRET_KEY_LENGTH, Settings
from app.db.base import Base
from app.items.models import Item
from app.media.models import ItemImage
from app.users.models import User

STRONG_KEY = "7Yq2Lp0dR4tZx8Wv3Nc6Mb1Kf9Hg5Js2Ae7Ud0Xo"


# --- 1. SECRET_KEY validation -------------------------------------------------


def test_empty_secret_key_rejected_in_production() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key="").resolve_secret_key()


def test_short_secret_key_rejected_in_production() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key="tooshort").resolve_secret_key()


@pytest.mark.parametrize("weak", ["changeme", "secret", "supersecret", "password", "test"])
def test_known_placeholders_are_not_usable_keys(weak: str) -> None:
    settings = Settings(secret_key=weak)
    assert settings.has_usable_secret_key is False
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key=weak).resolve_secret_key()


def test_placeholder_check_is_case_insensitive() -> None:
    assert Settings(secret_key="ChangeMe").has_usable_secret_key is False


@pytest.mark.parametrize(
    "padded",
    [
        "changeme" * 5,
        "a" * 40,
        "ab" * 20,
        "0123456789" * 4,
        "secret" * 6,
    ],
)
def test_placeholder_padded_to_minimum_length_is_rejected(padded: str) -> None:
    """Padding a placeholder must not make it an acceptable key."""
    assert len(padded) >= MIN_SECRET_KEY_LENGTH
    settings = Settings(app_env="production", secret_key=padded)
    assert settings.has_usable_secret_key is False
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.resolve_secret_key()


def test_realistic_random_key_is_accepted() -> None:
    key = secrets.token_urlsafe(64)
    assert Settings(app_env="production", secret_key=key).has_usable_secret_key is True


def test_strong_secret_key_is_used_verbatim() -> None:
    settings = Settings(app_env="production", secret_key=STRONG_KEY)
    assert settings.has_usable_secret_key is True
    assert settings.resolve_secret_key() == STRONG_KEY


def test_whitespace_only_secret_key_rejected() -> None:
    settings = Settings(app_env="production", secret_key=" " * 40)
    assert settings.has_usable_secret_key is False


def test_development_gets_random_key_instead_of_empty_one() -> None:
    first = Settings(app_env="development", secret_key="").resolve_secret_key()
    second = Settings(app_env="development", secret_key="").resolve_secret_key()
    assert len(first) >= MIN_SECRET_KEY_LENGTH
    assert first != second, "each process must get its own key, not a shared default"


def test_get_settings_never_returns_empty_secret_key() -> None:
    from app.config import get_settings

    assert len(get_settings().secret_key) >= MIN_SECRET_KEY_LENGTH


# --- shared DB fixture --------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_login_throttle() -> Iterator[None]:
    """Clear the module-level per-IP login throttle between tests.

    ``app.auth.routes._ip_attempts`` is process-global, so without this the
    combined login attempts of the whole suite trip the 20/minute limit.
    """
    from app.auth import routes as auth_routes

    auth_routes._ip_attempts.clear()
    yield
    auth_routes._ip_attempts.clear()


@pytest.fixture
async def db_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_fk(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.auth import routes as auth_routes
    from app.db import engine as db_engine

    orig_routes_factory = auth_routes._get_session_factory
    orig_factory = db_engine._get_session_factory
    orig_engine = db_engine._engine
    orig_session = db_engine._session_factory

    auth_routes._get_session_factory = lambda: factory
    db_engine._get_session_factory = lambda: factory
    db_engine._engine = None  # type: ignore[assignment]
    db_engine._session_factory = None  # type: ignore[assignment]

    yield factory

    auth_routes._get_session_factory = orig_routes_factory
    db_engine._get_session_factory = orig_factory
    db_engine._engine = orig_engine
    db_engine._session_factory = orig_session
    await engine.dispose()


async def _create_user(
    factory: async_sessionmaker[AsyncSession], *, email: str, role: str
) -> User:
    async with factory() as db:
        user = User(
            email=email,
            password_hash=hash_password("Supersecret1"),
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _login(client: AsyncClient, user: User) -> None:
    """Log in through the real form flow so the session cookie is set."""
    response = await client.post(
        "/auth/login",
        data={"email": user.email, "password": "Supersecret1"},
        follow_redirects=False,
    )
    assert client.cookies.get(COOKIE_SESSION), (
        f"login failed for {user.email}: {response.status_code}"
    )


# --- 2. /access search endpoints require admin --------------------------------

SEARCH_ENDPOINTS = [
    "/access/search/locations/json",
    "/access/search/categories/json",
    "/access/search/tags/json",
    "/access/search/items/json",
    "/access/users/json",
]


@pytest.mark.parametrize("endpoint", SEARCH_ENDPOINTS)
async def test_search_endpoints_reject_anonymous(
    endpoint: str, client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create_user(db_factory, email="victim@example.com", role="admin")
    response = await client.get(endpoint)
    assert response.status_code in (401, 303), response.status_code


@pytest.mark.parametrize("endpoint", SEARCH_ENDPOINTS)
async def test_search_endpoints_reject_non_admin(
    endpoint: str, client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await _create_user(db_factory, email="nosy@example.com", role="viewer")
    await _login(client, user)
    response = await client.get(endpoint)
    assert response.status_code == 403, response.status_code


@pytest.mark.parametrize("endpoint", SEARCH_ENDPOINTS)
async def test_search_endpoints_allow_admin(
    endpoint: str, client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await _create_user(db_factory, email="boss@example.com", role="admin")
    await _login(client, user)
    response = await client.get(endpoint)
    assert response.status_code == 200, response.text


async def test_users_search_does_not_leak_emails_to_anonymous(
    client: AsyncClient, db_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create_user(db_factory, email="secret.person@example.com", role="admin")
    response = await client.get("/access/users/json")
    assert "secret.person@example.com" not in response.text


# --- 3. serve_image_file honours access scopes --------------------------------


class _FakeStorage:
    def __init__(self, data: bytes = b"image-bytes") -> None:
        self.data = data

    async def download(self, path: str) -> bytes:
        return self.data


@pytest.fixture
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> _FakeStorage:
    from app.media import storage as storage_module

    backend = _FakeStorage()
    monkeypatch.setattr(storage_module, "get_storage_backend", lambda *a, **k: backend)
    return backend


async def _seed_item_with_image(
    factory: async_sessionmaker[AsyncSession], *, public: bool
) -> tuple[Item, ItemImage]:
    async with factory() as db:
        item = Item(name="Drill", short_code=f"DR{uuid.uuid4().hex[:5]}")
        db.add(item)
        await db.flush()

        image = ItemImage(
            item_id=item.id,
            storage_path=f"{item.id}/{uuid.uuid4()}-optimized.webp",
            mime_type="image/webp",
        )
        db.add(image)

        if public:
            scope = AccessScope(name="Public stuff", allow_anonymous=True)
            db.add(scope)
            await db.flush()
            db.add(AccessScopeRule(
                scope_id=scope.id, rule_type="specific_item", rule_value=str(item.id)
            ))
            db.add(AccessScopePermission(scope_id=scope.id, permission="view"))

        await db.commit()
        await db.refresh(item)
        await db.refresh(image)
        return item, image


async def test_image_file_blocked_for_anonymous_when_item_is_private(
    client: AsyncClient,
    db_factory: async_sessionmaker[AsyncSession],
    fake_storage: _FakeStorage,
) -> None:
    item, image = await _seed_item_with_image(db_factory, public=False)
    response = await client.get(f"/items/{item.id}/images/{image.id}/file")
    assert response.status_code == 403, response.status_code
    assert response.content != fake_storage.data


async def test_image_file_allowed_for_anonymous_when_item_is_public(
    client: AsyncClient,
    db_factory: async_sessionmaker[AsyncSession],
    fake_storage: _FakeStorage,
) -> None:
    item, image = await _seed_item_with_image(db_factory, public=True)
    response = await client.get(f"/items/{item.id}/images/{image.id}/file")
    assert response.status_code == 200, response.status_code
    assert response.content == fake_storage.data


async def test_image_file_blocked_for_user_without_scope(
    client: AsyncClient,
    db_factory: async_sessionmaker[AsyncSession],
    fake_storage: _FakeStorage,
) -> None:
    item, image = await _seed_item_with_image(db_factory, public=True)
    user = await _create_user(db_factory, email="stranger@example.com", role="viewer")
    await _login(client, user)
    response = await client.get(f"/items/{item.id}/images/{image.id}/file")
    assert response.status_code == 403, response.status_code


async def test_image_file_allowed_for_admin(
    client: AsyncClient,
    db_factory: async_sessionmaker[AsyncSession],
    fake_storage: _FakeStorage,
) -> None:
    item, image = await _seed_item_with_image(db_factory, public=False)
    user = await _create_user(db_factory, email="boss@example.com", role="admin")
    await _login(client, user)
    response = await client.get(f"/items/{item.id}/images/{image.id}/file")
    assert response.status_code == 200, response.status_code
    assert response.content == fake_storage.data


async def test_image_file_does_not_leak_across_items(
    client: AsyncClient,
    db_factory: async_sessionmaker[AsyncSession],
    fake_storage: _FakeStorage,
) -> None:
    _, public_image = await _seed_item_with_image(db_factory, public=True)
    private_item, private_image = await _seed_item_with_image(db_factory, public=False)
    # A public image id paired with a private item must not resolve.
    response = await client.get(f"/items/{private_item.id}/images/{public_image.id}/file")
    assert response.status_code == 403, response.status_code
    assert private_image.id != public_image.id
