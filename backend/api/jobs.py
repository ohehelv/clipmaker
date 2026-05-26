from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.models import User, UserSettings
from ..db.session import get_session
from ..jobs.queue import UserContext, job_queue
from ..schemas import JobInfo, JobRequest, SceneMode
from ..services.auth import get_current_user
from ..services.quota import check_can_generate, get_effective_keys

router = APIRouter()


@router.post("", response_model=JobInfo)
async def create_job(
    audio: UploadFile = File(...),
    prompt: str = Form(...),
    lyrics: str = Form(""),
    scene_mode: SceneMode = Form(SceneMode.whisper),
    generator: str = Form(settings.default_generator),
    n_scenes: int = Form(0),
    burn_subtitles: bool = Form(False),
    llm_detail: bool = Form(True),
    language: Optional[str] = Form(None),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    fps: Optional[int] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> JobInfo:
    user_settings = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    ).scalar_one_or_none()
    ws_key, orr_key = get_effective_keys(user, user_settings)

    check_can_generate(user, generator, ws_key)

    job_id = uuid.uuid4().hex[:12]
    job_dir = settings.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(audio.filename or "audio.mp3").suffix or ".mp3"
    audio_path = job_dir / f"input{suffix}"
    with audio_path.open("wb") as f:
        shutil.copyfileobj(audio.file, f)

    req = JobRequest(
        prompt=prompt,
        lyrics=lyrics,
        scene_mode=scene_mode,
        generator=generator,
        n_scenes=n_scenes,
        burn_subtitles=burn_subtitles,
        language=language,
        width=width,
        height=height,
        fps=fps,
        llm_detail=llm_detail,
    )
    (job_dir / "request.json").write_text(req.model_dump_json(indent=2), encoding="utf-8")

    ctx = UserContext(
        user_id=user.id,
        is_admin=user.is_admin,
        wavespeed_key=ws_key,
        openrouter_key=orr_key,
    )
    info = await job_queue.submit(job_id, audio_path, req, user_ctx=ctx)
    return info


@router.get("/{job_id}", response_model=JobInfo)
async def get_job(job_id: str, user: User = Depends(get_current_user)) -> JobInfo:
    info = job_queue.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="job not found")
    owner = job_queue.owner_of(job_id)
    if owner is not None and owner != user.id and not user.is_admin:
        raise HTTPException(status_code=404, detail="job not found")
    return info


@router.get("", response_model=list[JobInfo])
async def list_jobs(user: User = Depends(get_current_user)) -> list[JobInfo]:
    if user.is_admin:
        return job_queue.list()
    return job_queue.list(user_id=user.id)


@router.post("/clear")
async def clear_finished_jobs(user: User = Depends(get_current_user)) -> dict:
    n = job_queue.clear_finished()
    return {"removed": n}


@router.delete("/{job_id}")
async def cancel_job(job_id: str, user: User = Depends(get_current_user)) -> dict:
    owner = job_queue.owner_of(job_id)
    if owner is not None and owner != user.id and not user.is_admin:
        raise HTTPException(status_code=404, detail="job not found")
    ok = job_queue.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found or already finished")
    return {"cancelled": True}
