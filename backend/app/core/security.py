"""
Security utilities — JWT creation/verification and FastAPI auth dependencies.

OOP Design: This module acts as an **integration boundary** for authentication.
Module M1 (User & Auth) owns the full authentication implementation including
user registration, login flows, and password hashing. This module provides the
minimal JWT plumbing and FastAPI dependencies that *all* modules can rely on
for protecting endpoints.

The ``create_access_token`` / ``decode_access_token`` functions encapsulate the
token format so that swapping JWT libraries or adding refresh-token logic only
requires changes here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# ── Token helpers ────────────────────────────────────────────────────────────


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to embed in the token. Must include ``sub`` (user id)
              and ``role``.
        expires_delta: Custom expiration duration. Falls back to the
                       configured ``JWT_ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Args:
        token: The raw JWT string.

    Returns:
        The decoded payload dictionary.

    Raises:
        AuthenticationError: If the token is invalid, expired, or missing
                             the required ``sub`` claim.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("sub") is None:
            raise AuthenticationError("Token is missing the 'sub' claim.")
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Could not validate token: {exc}") from exc


# ── FastAPI Dependencies ─────────────────────────────────────────────────────


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    """FastAPI dependency that extracts and returns the authenticated user's ID.

    Reads the ``sub`` claim from the Bearer token and converts it to a UUID.

    Raises:
        HTTPException 401: If the token is invalid or the ``sub`` claim is not
                           a valid UUID.
    """
    try:
        payload = decode_access_token(token)
        return UUID(payload["sub"])
    except (AuthenticationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(*roles: str):
    """Factory that returns a FastAPI dependency enforcing role-based access.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_role("ADMIN"))])
        async def admin_endpoint(): ...

    Args:
        *roles: One or more role strings the caller must possess.

    Returns:
        An async dependency function that raises ``HTTPException 403`` when the
        token's ``role`` claim is not in the allowed set.
    """
    allowed = set(roles)

    async def _check_role(token: str = Depends(oauth2_scheme)) -> str:
        """Validate that the token's role claim is in the allowed set."""
        try:
            payload = decode_access_token(token)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user_role: str | None = payload.get("role")
        if user_role is None or user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' is not authorized. Required: {allowed}",
            )
        return user_role

    return _check_role
