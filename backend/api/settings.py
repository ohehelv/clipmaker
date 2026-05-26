"""GET/PUT /api/settings — управление пользовательскими API-ключами."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User, UserSettings
from ..db.session import get_session
from ..services.auth import get_current_user
from ..services.crypto import decrypt, encrypt, mask
from ..services.wavespeed import verify_key


router = APIRouter()


class SettingsView(BaseModel):
    has_wavespeed_key: bool
    wavespeed_key_masked: str = ""
    has_openrouter_key: bool
    openrouter_key_masked: str = ""
    default_model: str | None = None


class SettingsUpdate(BaseModel):
    wavespeed_key: str | None = Field(default=None, description="оставить null чтобы не менять, '' чтобы очистить")
    openrouter_key: str | None = Field(default=None)
    default_model: str | None = Field(default=None)


async def _get_or_create(db: AsyncSession, user: User) -> UserSettings:
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    ).scalar_one_or_none()
    if row is None:
        row = UserSettings(user_id=user.id)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("", response_model=SettingsView)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> SettingsView:
    s = await _get_or_create(db, user)
    ws = decrypt(s.wavespeed_key_enc)
    orr = decrypt(s.openrouter_key_enc)
    return SettingsView(
        has_wavespeed_key=bool(ws),
        wavespeed_key_masked=mask(ws),
        has_openrouter_key=bool(orr),
        openrouter_key_masked=mask(orr),
        default_model=s.default_model,
    )


@router.put("", response_model=SettingsView)
async def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> SettingsView:
    s = await _get_or_create(db, user)
    if payload.wavespeed_key is not None:
        s.wavespeed_key_enc = encrypt(payload.wavespeed_key.strip()) if payload.wavespeed_key.strip() else None
    if payload.openrouter_key is not None:
        s.openrouter_key_enc = encrypt(payload.openrouter_key.strip()) if payload.openrouter_key.strip() else None
    if payload.default_model is not None:
        s.default_model = payload.default_model.strip() or None
    await db.commit()
    await db.refresh(s)
    return await get_settings(user=user, db=db)


class VerifyResp(BaseModel):
    ok: bool
    message: str = ""


@router.post("/verify_wavespeed", response_model=VerifyResp)
async def verify_wavespeed(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> VerifyResp:
    s = await _get_or_create(db, user)
    key = decrypt(s.wavespeed_key_enc)
    if not key:
        raise HTTPException(status_code=400, detail="WaveSpeed key not set")
    ok = await verify_key(key)
    return VerifyResp(ok=ok, message="ключ принят" if ok else "ключ отклонён WaveSpeed")
