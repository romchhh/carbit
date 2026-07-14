from datetime import datetime, timedelta, UTC
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_cookies import ADMIN_COOKIE_NAME, AUTH_COOKIE_NAME
from app.core.config import settings

optional_bearer = HTTPBearer(auto_error=False)


def _decode_user_id(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("role") == "admin":
        raise JWTError()
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise JWTError()
    return user_id


def _extract_bearer_or_cookie(
    credentials: HTTPAuthorizationCredentials | None,
    cookie_token: str | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    if cookie_token:
        return cookie_token
    return None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    cookie_token: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
) -> str:
    """Accept Bearer OR HttpOnly cookie — same session for middleware and API."""
    token = _extract_bearer_or_cookie(credentials, cookie_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return _decode_user_id(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user_id_flexible(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    access_token: str | None = Query(None),
    cookie_token: str | None = Cookie(None, alias=AUTH_COOKIE_NAME),
) -> str:
    # Prefer Authorization / HttpOnly cookie; query token kept only as legacy fallback.
    token = _extract_bearer_or_cookie(credentials, cookie_token) or access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return _decode_user_id(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({"sub": subject, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_admin_token(expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(hours=12))
    return jwt.encode(
        {"sub": "admin", "role": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _decode_admin(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("role") != "admin":
        raise JWTError()
    return payload.get("sub", "admin")


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    cookie_token: str | None = Cookie(None, alias=ADMIN_COOKIE_NAME),
) -> str:
    """Accept Bearer OR HttpOnly admin cookie."""
    token = _extract_bearer_or_cookie(credentials, cookie_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return _decode_admin(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


async def get_current_admin_flexible(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    access_token: str | None = Query(None),
    cookie_token: str | None = Cookie(None, alias=ADMIN_COOKIE_NAME),
) -> str:
    token = _extract_bearer_or_cookie(credentials, cookie_token) or access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return _decode_admin(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
