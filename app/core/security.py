from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
SESSION_COOKIE_NAME = "dra_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_session_token(*, user_id: str, role: str, name: str, email: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "userId": user_id,
        "role": role,
        "name": name,
        "email": email,
        "iat": now,
        "exp": now + timedelta(seconds=SESSION_MAX_AGE_SECONDS),
    }
    return jwt.encode(payload, settings.AUTH_SECRET, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.AUTH_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None
