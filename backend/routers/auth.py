from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from db import get_db
from deps import get_current_user
from models import RefreshToken, School, User, UserRole
from rate_limiter import FixedWindowRateLimiter
from schemas import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserOut
from security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])
login_limiter = FixedWindowRateLimiter(
    max_requests=settings.login_rate_limit_count,
    window_seconds=settings.login_rate_limit_window_seconds,
)


@router.post("/bootstrap-manager", response_model=UserOut)
def bootstrap_manager(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if settings.app_env == "production" and not settings.allow_bootstrap_manager:
        raise HTTPException(status_code=403, detail="Bootstrap is disabled in production")
    school = db.scalar(select(School).order_by(School.id.asc()))
    if not school:
        school = School(name="Default School", active=True)
        db.add(school)
        db.flush()
    manager_exists = db.scalar(
        select(User.id).where(User.role == UserRole.MANAGER, User.school_id == school.id)
    )
    if manager_exists:
        raise HTTPException(status_code=400, detail="Manager already exists")
    if payload.role != UserRole.MANAGER:
        raise HTTPException(status_code=400, detail="Bootstrap must create MANAGER role")

    user = User(
        school_id=school.id,
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=payload.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    source_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{source_ip}:{payload.email.lower()}"
    if not login_limiter.allow(limiter_key):
        raise HTTPException(status_code=429, detail="Too many login attempts, try again later")

    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.active:
        raise HTTPException(status_code=403, detail="User is inactive")

    access_token = create_access_token(user.id, user.role)
    refresh_token, jti, expires_at = create_refresh_token(user.id, user.role)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token_payload = decode_access_token(payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token type")

    jti = token_payload.get("jti")
    user_id = int(token_payload.get("sub", "0"))
    if not jti or user_id <= 0:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    token_record = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if not token_record:
        raise HTTPException(status_code=401, detail="Unknown refresh token")
    if token_record.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if token_record.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="User is not active")

    token_record.revoked_at = datetime.now(timezone.utc)
    access_token = create_access_token(user.id, user.role)
    new_refresh, new_jti, new_expires_at = create_refresh_token(user.id, user.role)
    db.add(RefreshToken(user_id=user.id, jti=new_jti, expires_at=new_expires_at))
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> None:
    try:
        token_payload = decode_access_token(payload.refresh_token)
        jti = token_payload.get("jti")
    except Exception:  # noqa: BLE001
        return
    if not jti:
        return
    token_record = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if token_record and token_record.revoked_at is None:
        token_record.revoked_at = datetime.now(timezone.utc)
        db.commit()


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
