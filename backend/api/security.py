from __future__ import annotations

import secrets
from fastapi import Header, HTTPException

from ..config import settings


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Проверка API ключа. Если ключ не задан в env, доступ открыт."""
    expected = settings.api_key.strip()
    if not expected:
        return

    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()

    provided = (x_api_key or bearer or "").strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid api key")
