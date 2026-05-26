"""Гейтинг доступа к генерации.

Правила:
- Админ: всегда может (использует свой WaveSpeed-ключ если задан,
  иначе settings.wavespeed_api_key fallback; локальные ComfyUI — бесплатно).
- Обычный юзер: должен иметь свой WaveSpeed ключ в настройках.
"""

from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..db.models import User, UserSettings
from ..services.crypto import decrypt


def get_effective_keys(user: User, settings_row: UserSettings | None) -> tuple[str, str]:
    """Возвращает (wavespeed_key, openrouter_key) для конкретного юзера.

    OpenRouter — dual: личный ключ, иначе админский (fallback всем).
    WaveSpeed — только личный, либо админский только для админа.
    """
    ws_user = decrypt(settings_row.wavespeed_key_enc) if settings_row else ""
    orr_user = decrypt(settings_row.openrouter_key_enc) if settings_row else ""

    wavespeed = ws_user or (settings.wavespeed_api_key if user.is_admin else "")
    openrouter = orr_user or settings.openrouter_api_key
    return wavespeed, openrouter


def check_can_generate(user: User, generator_name: str, wavespeed_key: str) -> None:
    """Бросает 402, если юзер без ключа пытается запустить облачную генерацию."""
    from ..generators.registry import get as get_gen

    try:
        gen = get_gen(generator_name)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_local = getattr(gen, "local", False)
    if is_local:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="local generators are admin-only")
        return  # локалка для админа всегда ок

    # Облачные (WaveSpeed) — нужен ключ.
    if not wavespeed_key:
        raise HTTPException(
            status_code=402,
            detail="WaveSpeed API ключ не задан. Добавьте его в Настройках.",
        )
