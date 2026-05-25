from __future__ import annotations

from fastapi import APIRouter

from ..generators.registry import list_generators
from ..schemas import GeneratorInfo

router = APIRouter()


@router.get("", response_model=list[GeneratorInfo])
async def models_list() -> list[GeneratorInfo]:
    return list_generators()
