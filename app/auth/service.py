from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pyotp
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.users.models import User

logger = logging.getLogger(__name__)

pwd_context = PasswordHash([Argon2Hasher()])

COOKIE_SESSION = "nesti_session"
COOKIE_PENDING_2FA = "nesti_pending_2fa"
TOKEN_EXPIRE_DAYS = 7
PENDING_2FA_EXPIRE_MINUTES = 5


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    email: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session_token(user_id: str, email: str) -> str:
    settings = get_settings()
    return str(
        jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "typ": "session",
                "exp": datetime.now(UTC) + timedelta(days=TOKEN_EXPIRE_DAYS),
            },
            settings.secret_key,
            algorithm="HS256",
        )
    )


def create_pending_2fa_token(user_id: str) -> str:
    settings = get_settings()
    return str(
        jwt.encode(
            {
                "sub": user_id,
                "typ": "pending_2fa",
                "exp": datetime.now(UTC) + timedelta(minutes=PENDING_2FA_EXPIRE_MINUTES),
            },
            settings.secret_key,
            algorithm="HS256",
        )
    )


def verify_session_token(token: str) -> AuthUser | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=["HS256"]
        )
    except JWTError:
        return None
    if payload.get("typ") != "session":
        return None
    sub: object | None = payload.get("sub")
    if sub is None:
        return None
    user_id = str(sub)
    email = str(payload.get("email") or "")
    return AuthUser(user_id=user_id, email=email)


def verify_pending_2fa_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=["HS256"]
        )
    except JWTError:
        return None
    if payload.get("typ") != "pending_2fa":
        return None
    user_id: str | None = payload.get("sub")
    return user_id


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(email: str, secret: str) -> str:
    totp = pyotp.TOTP(secret, interval=30, digits=6)
    return totp.provisioning_uri(name=email, issuer_name="Nesti")


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret, interval=30, digits=6)
    return totp.verify(code, valid_window=1)


async def bootstrap_admin(db: AsyncSession) -> None:
    """Upsert admin user from ADMIN_EMAIL / ADMIN_PASSWORD env vars."""
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        return
    stmt = select(User).where(User.email == settings.admin_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        db.add(
            User(
                supabase_id=f"bootstrap-{settings.admin_email}",
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                is_active=True,
            )
        )
        await db.commit()
        logger.info("Bootstrapped admin user: %s", settings.admin_email)
    elif user.password_hash is None:
        user.password_hash = hash_password(settings.admin_password)
        await db.commit()
        logger.info("Set password for existing admin: %s", settings.admin_email)
