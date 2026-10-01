import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
import jwt
import bcrypt
from app.config import settings

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

get_password_hash = hash_password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def create_access_token(user_id: str, email: str, role: str) -> str:
    """
    Generate short-lived JWT Access Token (default 15 minutes).
    [SCRUM-34 / SCRUM-103]
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str, remember_me: bool = False) -> Tuple[str, datetime]:
    """
    Generate long-lived JWT Refresh Token (7 days, or 30 days if rememberMe).
    Returns (token_string, expires_datetime).
    [SCRUM-34 / SCRUM-103]
    """
    days = settings.REMEMBER_ME_EXPIRE_DAYS if remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
    now = datetime.now(timezone.utc)
    expire_dt = now + timedelta(days=days)

    payload: Dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire_dt.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token_str = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    # Return naive UTC datetime for DB storage
    return token_str, expire_dt.replace(tzinfo=None)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate signature and expiry of a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]}
        )
        return payload
    except jwt.PyJWTError:
        return None
