import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from config import settings
from models import UserRole


ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
    return hmac.compare_digest(digest, expected)


def _encode_token(payload: dict) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: int, role: UserRole) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "role": role.value, "exp": expire, "type": "access"}
    return _encode_token(payload)


def create_refresh_token(user_id: int, role: UserRole) -> tuple[str, str, datetime]:
    jti = uuid.uuid4().hex
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
        "type": "refresh",
        "jti": jti,
    }
    return _encode_token(payload), jti, expire


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
