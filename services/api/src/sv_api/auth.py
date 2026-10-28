from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
from typing import Any, Dict, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sv_api.database import get_db
from sv_api.models import ApiKey, AuditLog, User
from sv_core.settings import settings

ph = PasswordHasher()
security = HTTPBearer(auto_error=False)

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token (default 15 minutes)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token (7 days)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_api_key() -> str:
    """Generate plaintext API key in sv_live_ hex format."""
    return f"sv_live_{secrets.token_hex(20)}"


def hash_api_key(api_key: str) -> str:
    """Hash API key using SHA-256 for persistent database storage."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def get_current_user_or_key(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Authenticate request using either Bearer JWT or X-API-Key header."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # 1. Check API Key
    if x_api_key:
        hashed = hash_api_key(x_api_key)
        stmt = select(ApiKey).where(ApiKey.key_hash == hashed, ApiKey.is_active.is_(True))
        res = await db.execute(stmt)
        key_record = res.scalars().first()
        if not key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key"
            )
        # Update last_used_at
        key_record.last_used_at = now
        await db.commit()
        return {"type": "api_key", "user_id": key_record.user_id, "key_id": key_record.id}

    # 2. Check Bearer Token
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            return {"type": "jwt", "user_id": user_id, "claims": payload}
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials (Bearer token or X-API-Key)"
    )


async def record_audit_log(
    db: AsyncSession,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Record an immutable audit log entry."""
    audit = AuditLog(
        id=f"aud_{secrets.token_hex(16)}",
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details or {}),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    await db.commit()
