from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..core.prompts_store import get_prompts, reset_prompts, save_prompts

router = APIRouter()


class PromptsBody(BaseModel):
    director_system: str
    detail_system: str


@router.get("")
def read_prompts() -> dict:
    return dict(get_prompts())


@router.put("")
def update_prompts(body: PromptsBody) -> dict:
    return dict(save_prompts({
        "director_system": body.director_system,
        "detail_system": body.detail_system,
    }))


@router.post("/reset")
def reset() -> dict:
    return dict(reset_prompts())
