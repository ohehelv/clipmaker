from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import settings
from ..jobs.queue import job_queue
from ..schemas import JobInfo, JobRequest, SceneMode

router = APIRouter()


@router.post("", response_model=JobInfo)
async def create_job(
    audio: UploadFile = File(...),
    prompt: str = Form(...),
    lyrics: str = Form(""),
    scene_mode: SceneMode = Form(SceneMode.whisper),
    generator: str = Form("wan"),
    n_scenes: int = Form(0),
    burn_subtitles: bool = Form(False),
    llm_detail: bool = Form(True),
    language: Optional[str] = Form(None),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    fps: Optional[int] = Form(None),
) -> JobInfo:
    job_id = uuid.uuid4().hex[:12]
    job_dir = settings.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # сохранить аудио
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

    info = await job_queue.submit(job_id, audio_path, req)
    return info


@router.get("/{job_id}", response_model=JobInfo)
async def get_job(job_id: str) -> JobInfo:
    info = job_queue.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="job not found")
    return info


@router.get("", response_model=list[JobInfo])
async def list_jobs() -> list[JobInfo]:
    return job_queue.list()


@router.post("/clear")
async def clear_finished_jobs() -> dict:
    n = job_queue.clear_finished()
    return {"removed": n}


@router.delete("/{job_id}")
async def cancel_job(job_id: str) -> dict:
    ok = job_queue.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found or already finished")
    return {"cancelled": True}
