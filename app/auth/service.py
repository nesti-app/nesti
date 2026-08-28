from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass

import httpx
from jose import JWTError, jwt
from jose.jwk import construct as jwk_construct

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthUser:
    supabase_id: str
    email: str


def _derive_es256_public_key(private_key_data: dict):
    """Derive ES256 public JWK from private key (strip the private component 'd')."""
    public_jwk = {k: v for k, v in private_key_data.items() if k != "d"}
    public_jwk["key_ops"] = ["verify"]
    return jwk_construct(public_jwk)


def _fetch_local_es256_key():
    """Fetch ES256 public key from local Supabase auth container env."""
    settings = get_settings()
    if not settings.supabase_url:
        return None
    try:
        result = subprocess.run(
            [
                "podman",
                "exec",
                "supabase_auth_nesti",
                "env",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.startswith("GOTRUE_JWT_KEYS="):
                raw = line.split("=", 1)[1]
                keys = json.loads(raw)
                for key_data in keys:
                    if key_data.get("alg") == "ES256" and "d" in key_data:
                        return _derive_es256_public_key(key_data)
    except Exception as e:
        logger.debug("Could not fetch local ES256 key: %s", e)
    return None


class AuthService:
    """Abstraction over Supabase Auth. No Supabase-specific code leaks into routes."""

    def __init__(self) -> None:
        settings = get_settings()
        self._supabase_url = settings.supabase_url
        self._publishable_key = settings.effective_publishable_key
        self._service_key = settings.effective_secret_key
        self._legacy_anon_key = settings.supabase_anon_key
        self._jwt_secret = settings.supabase_jwt_secret
        self._secret_key = settings.secret_key
        self._es256_key = None
        self._jwks_keys: dict[str, object] | None = None
        self._jwks_loaded = False

    def _get_es256_key(self):
        if self._es256_key is None:
            self._es256_key = _fetch_local_es256_key()
        return self._es256_key

    def _service_auth_headers(self) -> dict[str, str]:
        """Auth headers for privileged (admin/Storage) calls.

        The modern `sb_secret_...` key is sent on the `apikey` header only --
        Supabase rejects it in `Authorization: Bearer`. The legacy JWT-based
        `service_role` key additionally uses Bearer. Both are sent on `apikey`.
        """
        headers = {"apikey": self._service_key}
        if self._service_key and not self._service_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self._service_key}"
        return headers

    async def load_jwks(self) -> None:
        """Fetch Supabase JWKS signing keys and cache them for token verification.

        Modern Supabase projects sign JWTs with ES256 keys exposed via a JWKS
        endpoint instead of the legacy shared HS256 JWT secret.
        """
        if self._jwks_loaded:
            return
        self._jwks_loaded = True
        if not self._supabase_url:
            return
        jwks_url = f"{self._supabase_url}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(jwks_url, timeout=10.0)
                if resp.status_code != 200:
                    logger.warning("Failed to fetch JWKS (%s)", resp.status_code)
                    return
                keys = resp.json().get("keys", [])
                self._jwks_keys = {}
                for k in keys:
                    try:
                        self._jwks_keys[k["kid"]] = jwk_construct(k)
                    except Exception:
                        logger.warning("Skipping unparsable JWK: %s", k.get("kid"))
            except httpx.HTTPError:
                logger.exception("JWKS fetch error")

    def _verify_with_jwks(self, token: str) -> dict | None:
        """Verify a token against cached Supabase JWKS public keys."""
        if not self._jwks_keys:
            return None
        try:
            headers = jwt.get_unverified_header(token)
        except JWTError:
            return None
        key = self._jwks_keys.get(headers.get("kid"))
        if key is None:
            # Retry without kid match against the (single) available key
            if len(self._jwks_keys) == 1:
                key = next(iter(self._jwks_keys.values()))
            else:
                return None
        try:
            return jwt.decode(
                token,
                key,
                algorithms=["ES256", "RS256", "HS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            return None

    def create_signed_session(self, access_token: str, refresh_token: str) -> dict[str, str]:
        """Create a signed session cookie payload from Supabase tokens."""
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def verify_token(self, token: str) -> AuthUser | None:
        """Verify a Supabase JWT and return the user.

        Tries (in order):
        1. JWKS public keys (modern Supabase: ES256 / RS256 signing keys)
        2. HS256 with supabase_jwt_secret (legacy Supabase shared secret)
        3. ES256 with local Supabase EC key (local dev)
        4. HS256 with supabase_anon_key (legacy fallback)
        """
        # 1. JWKS-based verification (modern signing keys)
        payload = self._verify_with_jwks(token)
        if payload is not None:
            return self._extract_user(payload)

        # 2. Legacy HS256 shared secret
        if self._jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    self._jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                return self._extract_user(payload)
            except JWTError:
                pass

        # 3. Local Supabase ES256 key (local dev)
        es_key = self._get_es256_key()
        if es_key is not None:
            try:
                payload = jwt.decode(
                    token,
                    es_key,
                    algorithms=["ES256"],
                    options={"verify_aud": False},
                )
                return self._extract_user(payload)
            except JWTError:
                pass

        # 4. Legacy anon-key fallback
        if self._legacy_anon_key:
            try:
                payload = jwt.decode(
                    token,
                    self._legacy_anon_key,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                return self._extract_user(payload)
            except JWTError:
                pass

        logger.debug("Invalid JWT token")
        return None

    def _extract_user(self, payload: dict) -> AuthUser | None:
        supabase_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")
        if not supabase_id or not email:
            return None
        return AuthUser(supabase_id=supabase_id, email=email)

    async def exchange_code_for_session(self, code: str) -> dict[str, str] | None:
        """Exchange an OAuth authorization code for Supabase tokens."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._supabase_url}/auth/v1/token?grant_type=authorization_code",
                    json={"auth_code": code},
                    headers={
                        "apikey": self._publishable_key,
                        "Content-Type": "application/json",
                    },
                    timeout=10.0,
                )
                if resp.status_code != 200:
                    logger.warning("Token exchange failed: %s", resp.status_code)
                    return None
                data = resp.json()
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                if not access_token or not refresh_token:
                    return None
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            except httpx.HTTPError:
                logger.exception("Supabase token exchange error")
                return None

    async def refresh_session(self, refresh_token: str) -> dict[str, str] | None:
        """Refresh a Supabase session using a refresh token."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._supabase_url}/auth/v1/token?grant_type=refresh_token",
                    json={"refresh_token": refresh_token},
                    headers={
                        "apikey": self._publishable_key,
                        "Content-Type": "application/json",
                    },
                    timeout=10.0,
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                access_token = data.get("access_token")
                new_refresh_token = data.get("refresh_token")
                if not access_token or not new_refresh_token:
                    return None
                return {
                    "access_token": access_token,
                    "refresh_token": new_refresh_token,
                }
            except httpx.HTTPError:
                logger.exception("Supabase session refresh error")
                return None

    async def get_supabase_login_url(self, redirect_to: str | None = None) -> str:
        """Get the Supabase hosted login page URL."""
        params = f"?redirect_to={redirect_to}" if redirect_to else ""
        return f"{self._supabase_url}/auth/v1/authorize{params}"

    async def sign_out(self, access_token: str) -> bool:
        """Sign out from Supabase (invalidate the refresh token)."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._supabase_url}/auth/v1/logout",
                    headers={
                        "apikey": self._publishable_key,
                        "Authorization": f"Bearer {access_token}",
                    },
                    timeout=10.0,
                )
                return resp.status_code == 204
            except httpx.HTTPError:
                logger.exception("Supabase sign out error")
                return False

    async def admin_create_user(self, email: str, password: str) -> str | None:
        """Create a Supabase Auth user via Admin API. Returns the supabase_id."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._supabase_url}/auth/v1/admin/users",
                    json={"email": email, "password": password, "email_confirm": True},
                    headers={
                        **self._service_auth_headers(),
                        "Content-Type": "application/json",
                    },
                    timeout=10.0,
                )
                if resp.status_code not in (200, 201):
                    logger.warning(
                        "Supabase admin create user failed: %s %s",
                        resp.status_code,
                        resp.text,
                    )
                    return None
                return resp.json().get("id")
            except httpx.HTTPError:
                logger.exception("Supabase admin create user error")
                return None

    async def admin_update_password(self, supabase_id: str, password: str) -> bool:
        """Update a Supabase Auth user's password via Admin API."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.put(
                    f"{self._supabase_url}/auth/v1/admin/users/{supabase_id}",
                    json={"password": password},
                    headers={
                        **self._service_auth_headers(),
                        "Content-Type": "application/json",
                    },
                    timeout=10.0,
                )
                if resp.status_code != 200:
                    logger.warning(
                        "Supabase admin update password failed: %s %s",
                        resp.status_code,
                        resp.text,
                    )
                    return False
                return True
            except httpx.HTTPError:
                logger.exception("Supabase admin update password error")
                return False

    async def admin_delete_user(self, supabase_id: str) -> bool:
        """Delete a Supabase Auth user via Admin API."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.delete(
                    f"{self._supabase_url}/auth/v1/admin/users/{supabase_id}",
                    headers=self._service_auth_headers(),
                    timeout=10.0,
                )
                if resp.status_code not in (200, 204):
                    logger.warning(
                        "Supabase admin delete user failed: %s %s",
                        resp.status_code,
                        resp.text,
                    )
                    return False
                return True
            except httpx.HTTPError:
                logger.exception("Supabase admin delete user error")
                return False


auth_service = AuthService()
