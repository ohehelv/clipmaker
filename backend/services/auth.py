"""Аутентификация: bcrypt + JWT в httponly cookie."""

from __future__ import annotations

import time
from typing import Optional

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.session import get_session
from ..db.models import User


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str:
    return _pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return _pwd.verify(p, h)
    except Exception:
        return False


def _jwt_encode(user_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + settings.session_max_age_days * 86400,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _jwt_decode(token: str) -> Optional[int]:
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def set_session_cookie(response: Response, user_id: int) -> None:
    token = _jwt_encode(user_id)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Текущий пользователь из cookie. 401 если нет/невалиден."""
    token = request.cookies.get(settings.session_cookie_name)
    user = await _user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    token = request.cookies.get(settings.session_cookie_name)
    return await _user_from_token(token, db)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    return user


async def _user_from_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    if not token:
        return None
    uid = _jwt_decode(token)
    if uid is None:
        return None
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    return user
