"""Authentication, authorization, and cryptographic token management."""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def require_bearer(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> str:
    """Validate Bearer token for operators and API clients."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(credentials.credentials, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def require_device_token(x_device_token: Optional[str] = Header(default=None)) -> str:
    """Validate X-Device-Token header for IoT devices (ESP32)."""
    if x_device_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-Token header",
        )
    if not secrets.compare_digest(x_device_token, settings.device_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
        )
    return x_device_token


def generate_approval_token() -> str:
    """Generate a high-entropy, URL-safe approval token."""
    return f"apr_{secrets.token_urlsafe(32)}"
