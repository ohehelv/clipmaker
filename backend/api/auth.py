"""POST /api/auth/register, /login, /logout, GET /me."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.models import User, UserSettings
from ..db.session import get_session
from ..services.auth import (
    clear_session_cookie,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)


router = APIRouter()


class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class MeResp(BaseModel):
    id: int
    email: str
    is_admin: bool


def _is_admin_email(email: str) -> bool:
    return email.lower().strip() in settings.admin_emails_list


@router.post("/register", response_model=MeResp, status_code=201)
async def register(
    payload: RegisterReq,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> MeResp:
    existing = (
        await db.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        is_admin=_is_admin_email(payload.email),
    )
    user.settings = UserSettings()
    db.add(user)
    await db.commit()
    await db.refresh(user)

    set_session_cookie(response, user.id)
    return MeResp(id=user.id, email=user.email, is_admin=user.is_admin)


@router.post("/login", response_model=MeResp)
async def login(
    payload: LoginReq,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> MeResp:
    user = (
        await db.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Подтянуть админство если email добавили в env уже после регистрации.
    if not user.is_admin and _is_admin_email(user.email):
        user.is_admin = True
        await db.commit()

    set_session_cookie(response, user.id)
    return MeResp(id=user.id, email=user.email, is_admin=user.is_admin)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    clear_session_cookie(response)
    return Response(status_code=204)


@router.get("/me", response_model=MeResp)
async def me(user: User = Depends(get_current_user)) -> MeResp:
    return MeResp(id=user.id, email=user.email, is_admin=user.is_admin)
