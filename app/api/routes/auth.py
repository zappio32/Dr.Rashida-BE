from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_session
from app.core.security import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import PatientProfile, User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, SessionUser
from app.utils.ids import new_id

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, *, user_id: str, role: str, name: str, email: str) -> None:
    settings = get_settings()
    is_production = settings.NODE_ENV == "production"
    token = create_session_token(user_id=user_id, role=role, name=name, email=email)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
        max_age=SESSION_MAX_AGE_SECONDS,
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    try:
        result = await db.execute(select(User).where(User.email == payload.email.lower()))
        user = result.scalar_one_or_none()
        if not user or not user.isActive or not verify_password(payload.password, user.passwordHash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
        _set_session_cookie(response, user_id=user.id, role=user.role.value, name=user.name, email=user.email)
        return LoginResponse(role=user.role.value)
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001
        print(f"[auth/login] request failed: {error}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid login request.") from error


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    try:
        result = await db.execute(select(User).where(User.email == payload.email.lower()))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists.")
        user = User(
            id=new_id(),
            name=payload.name,
            email=payload.email.lower(),
            passwordHash=hash_password(payload.password),
            role=Role.PATIENT,
        )
        db.add(user)
        await db.flush()
        db.add(PatientProfile(id=new_id(), userId=user.id))
        await db.commit()
        _set_session_cookie(response, user_id=user.id, role=user.role.value, name=user.name, email=user.email)
        return RegisterResponse(ok=True)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as error:  # noqa: BLE001
        await db.rollback()
        print(f"[auth/register] request failed: {error}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create account.") from error


@router.post("/logout")
async def logout(response: Response) -> dict:
    settings = get_settings()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", domain=settings.COOKIE_DOMAIN or None)
    return {"ok": True}


@router.get("/session", response_model=SessionUser)
async def read_session(session: SessionUser = Depends(get_current_session)) -> SessionUser:
    return session
