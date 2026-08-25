from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

_JWT_ALGORITHM = "HS256"


@dataclass(frozen=True)
class AuthUser:
    supabase_id: str
    email: str


class AuthService:
    """Abstraction over Supabase Auth. No Supabase-specific code leaks into routes."""

    def __init__(self) -> None:
        settings = get_settings()
        self._supabase_url = settings.supabase_url
        self._supabase_anon_key = settings.supabase_anon_key
        self._supabase_service_key = settings.supabase_service_role_key
        self._secret_key = settings.secret_key

    def create_signed_session(self, access_token: str, refresh_token: str) -> dict[str, str]:
        """Create a signed session cookie payload from Supabase tokens."""
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def verify_token(self, token: str) -> AuthUser | None:
        """Verify a Supabase JWT and return the user."""
        try:
            payload = jwt.decode(
                token,
                self._supabase_anon_key,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            supabase_id: str | None = payload.get("sub")
            email: str | None = payload.get("email")
            if not supabase_id or not email:
                return None
            return AuthUser(supabase_id=supabase_id, email=email)
        except JWTError:
            logger.debug("Invalid JWT token")
            return None

    async def exchange_code_for_session(self, code: str) -> dict[str, str] | None:
        """Exchange an OAuth authorization code for Supabase tokens."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._supabase_url}/auth/v1/token?grant_type=authorization_code",
                    json={"auth_code": code},
                    headers={
                        "apikey": self._supabase_anon_key,
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
                        "apikey": self._supabase_anon_key,
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
                        "apikey": self._supabase_anon_key,
                        "Authorization": f"Bearer {access_token}",
                    },
                    timeout=10.0,
                )
                return resp.status_code == 204
            except httpx.HTTPError:
                logger.exception("Supabase sign out error")
                return False


auth_service = AuthService()
