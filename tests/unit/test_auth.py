from __future__ import annotations

import base64
from unittest.mock import AsyncMock, Mock

from cryptography.hazmat.primitives.asymmetric import ec
from httpx import AsyncClient
from jose import jwt
from jose.jwk import construct as jwk_construct
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService, AuthUser
from app.dependencies import get_db
from app.users.service import ensure_user_exists


def test_auth_service_verify_token_invalid() -> None:
    """Test that verify_token returns None for invalid tokens."""
    service = AuthService()
    result = service.verify_token("invalid.token.here")
    assert result is None


def test_auth_user_dataclass() -> None:
    """Test AuthUser dataclass creation."""
    user = AuthUser(supabase_id="abc-123", email="test@example.com")
    assert user.supabase_id == "abc-123"
    assert user.email == "test@example.com"


async def test_ensure_user_exists_first_user_becomes_admin() -> None:
    """First user auto-created in empty DB is bootstrapped as admin."""
    db = AsyncMock(spec=AsyncSession)
    exec_mock = Mock()
    exec_mock.scalar_one_or_none.return_value = None  # user not found yet
    exec_mock.scalar_one.return_value = 0  # empty database
    db.execute.return_value = exec_mock

    user = await ensure_user_exists(db, "sb-first", "first@example.com")

    assert user.role == "admin"
    added = db.add.call_args.args[0]
    assert added.role == "admin"
    assert added.supabase_id == "sb-first"


async def test_ensure_user_exists_second_user_is_viewer() -> None:
    """Subsequent auto-created users default to viewer."""
    db = AsyncMock(spec=AsyncSession)
    exec_mock = Mock()
    exec_mock.scalar_one_or_none.return_value = None  # user not found yet
    exec_mock.scalar_one.return_value = 1  # one user already exists
    db.execute.return_value = exec_mock

    user = await ensure_user_exists(db, "sb-second", "second@example.com")

    assert user.role == "viewer"
    added = db.add.call_args.args[0]
    assert added.role == "viewer"


async def test_login_page_renders(client: AsyncClient) -> None:
    """Test that login page renders."""
    response = await client.get("/auth/login")
    assert response.status_code == 200


async def test_logout_redirects(client: AsyncClient) -> None:
    """Test that logout redirects to login page."""
    response = await client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


async def test_protected_route_without_auth(client: AsyncClient) -> None:
    """Test that admin routes reject unauthenticated requests."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    mock_session.commit = AsyncMock()

    from app.main import app

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = await client.get("/admin/users", follow_redirects=False)
        assert response.status_code in (303, 401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _make_es256_jwk_and_token(kid: str) -> tuple[dict, str]:
    """Generate an ES256 (P-256) keypair, build a public JWK, and sign a token."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    numbers = public_key.public_numbers()
    x = numbers.x.to_bytes(32, "big")
    y = numbers.y.to_bytes(32, "big")
    def b64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    jwk_pub = {
        "kty": "EC",
        "crv": "P-256",
        "kid": kid,
        "alg": "ES256",
        "use": "sig",
        "x": b64url(x),
        "y": b64url(y),
    }

    token = jwt.encode(
        {"sub": "user-123", "email": "jwk@example.com"},
        private_key,
        algorithm="ES256",
        headers={"kid": kid},
    )
    return jwk_pub, token


def test_verify_token_with_jwks() -> None:
    """A modern ES256-signed token verifies against cached JWKS public keys."""
    kid = "8476853d-dcb8-4730-8c7e-c841a2f08a2a"
    jwk_pub, token = _make_es256_jwk_and_token(kid)

    service = AuthService()
    service._jwks_keys = {kid: jwk_construct(jwk_pub)}

    user = service.verify_token(token)
    assert user is not None
    assert user.email == "jwk@example.com"


def test_verify_token_with_jwks_wrong_key() -> None:
    """A token signed by a different key than the cached JWKS is rejected."""
    _, token_a = _make_es256_jwk_and_token("key-a")
    jwk_b, _ = _make_es256_jwk_and_token("key-b")

    service = AuthService()
    # JWKS only contains key-b, but the token was signed by key-a
    service._jwks_keys = {"key-b": jwk_construct(jwk_b)}

    assert service.verify_token(token_a) is None
