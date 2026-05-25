"""Live-загрузка системных промтов из data/prompts.json.

Файл создаётся при первом обращении из дефолтов в prompts.py.
При каждом вызове get_prompts() файл перечитывается — правки
через UI или вручную применяются без перезапуска сервера.
"""

from __future__ import annotations

import json
from typing import TypedDict

from ..config import settings
from . import prompts as _defaults


class PromptSet(TypedDict):
    director_system: str
    detail_system: str


def _path():
    return settings.data_dir / "prompts.json"


def _defaults_dict() -> PromptSet:
    return {
        "director_system": _defaults.DIRECTOR_SYSTEM,
        "detail_system": _defaults.DETAIL_SYSTEM,
    }


def get_prompts() -> PromptSet:
    p = _path()
    if not p.exists():
        save_prompts(_defaults_dict())
        return _defaults_dict()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _defaults_dict()
    base = _defaults_dict()
    base["director_system"] = str(data.get("director_system") or base["director_system"]).strip() or base["director_system"]
    base["detail_system"] = str(data.get("detail_system") or base["detail_system"]).strip() or base["detail_system"]
    return base


def save_prompts(data: PromptSet) -> PromptSet:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    cleaned: PromptSet = {
        "director_system": (data.get("director_system") or "").strip() or _defaults.DIRECTOR_SYSTEM,
        "detail_system": (data.get("detail_system") or "").strip() or _defaults.DETAIL_SYSTEM,
    }
    p.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    return cleaned


def reset_prompts() -> PromptSet:
    return save_prompts(_defaults_dict())
