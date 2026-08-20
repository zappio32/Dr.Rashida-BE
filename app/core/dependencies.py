from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.security import SESSION_COOKIE_NAME, decode_session_token
from app.schemas.auth import SessionUser


def get_optional_session(request: Request) -> SessionUser | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    payload = decode_session_token(token)
    if not payload:
        return None
    try:
        return SessionUser(userId=payload["userId"], role=payload["role"], name=payload["name"], email=payload["email"])
    except (KeyError, TypeError):
        return None


def get_current_session(session: SessionUser | None = Depends(get_optional_session)) -> SessionUser:
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return session


def require_role(*roles: str) -> Callable[[SessionUser], SessionUser]:
    def dependency(session: SessionUser = Depends(get_current_session)) -> SessionUser:
        if session.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this information.")
        return session

    return dependency
