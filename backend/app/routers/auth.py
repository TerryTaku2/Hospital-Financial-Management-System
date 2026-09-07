import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import is_main_branch_user
from app.config import settings
from app.database import get_db
from app.demo_data import ensure_demo_data
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    verify_password,
)


async def _build_user_out(db: AsyncSession, user: User) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True).model_copy(
        update={"can_view_all_branches": await is_main_branch_user(db, user)}
    )

router = APIRouter(prefix="/api/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


def _set_session_cookies(response: Response, user_id: int) -> None:
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    csrf_token = generate_csrf_token()

    response.set_cookie(
        ACCESS_COOKIE, access_token, httponly=True, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.access_token_expire_minutes * 60, path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, httponly=True, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400, path="/api/auth",
    )
    response.set_cookie(
        CSRF_COOKIE, csrf_token, httponly=False, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400, path="/",
    )


@router.post("/login", response_model=UserOut)
async def login(credentials: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    user = (await db.execute(select(User).where(User.username == credentials.username))).scalars().first()
    if user is None or not user.is_active or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    _set_session_cookies(response, user.id)
    return await _build_user_out(db, user)


@router.post("/demo-login", response_model=UserOut)
async def demo_login(response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    """Public, no-credentials entry point: wipes the entire database back to
    a fresh, richly seeded demo state and logs straight in as its admin
    user. This app has no tenant isolation, so this endpoint is only safe
    because this deployment is a demo/pitch instance — never point it at
    real patient data."""
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demo login is not enabled on this deployment")
    admin = await ensure_demo_data(db)
    _set_session_cookies(response, admin.id)
    return await _build_user_out(db, admin)


@router.post("/refresh", response_model=UserOut)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    user = await db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    _set_session_cookies(response, user.id)
    return await _build_user_out(db, user)


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UserOut:
    return await _build_user_out(db, user)
