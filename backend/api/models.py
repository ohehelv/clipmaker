from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from ..db.models import User
from ..generators.registry import list_generators
from ..schemas import GeneratorInfo
from ..services.auth import get_current_user_optional

router = APIRouter()


@router.get("", response_model=list[GeneratorInfo])
async def models_list(
    user: Optional[User] = Depends(get_current_user_optional),
) -> list[GeneratorInfo]:
    include_local = bool(user and user.is_admin)
    return list_generators(include_local=include_local)
