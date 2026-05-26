"""Шифрование пользовательских API-ключей через Fernet.

Ключ Fernet выводится из settings.secret_key через HKDF-SHA256, чтобы
SECRET_KEY можно было задавать как обычную строку (не base64).
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


def _derive_fernet_key() -> bytes:
    """Берём SHA-256 от secret_key и кодируем в urlsafe base64 (Fernet требует 32 байта)."""
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_FERNET = Fernet(_derive_fernet_key())


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    return _FERNET.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str | None) -> str:
    if not token:
        return ""
    try:
        return _FERNET.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask(plain: str) -> str:
    """Безопасное представление для UI: первые/последние 4 символа."""
    if not plain:
        return ""
    if len(plain) <= 8:
        return "*" * len(plain)
    return f"{plain[:4]}…{plain[-4:]}"
