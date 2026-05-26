"""In-process очередь задач: один воркер (один GPU), персист на диск, cancel, retry."""

from __future__ import annotations

import asyncio
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from ..config import settings
from ..schemas import JobInfo, JobRequest, JobStatus
from . import runner


class CancelledError(Exception):
    pass


@dataclass
class UserContext:
    """Контекст пользователя для job: id и расшифрованные ключи (живут в памяти)."""
    user_id: int = 0
    is_admin: bool = False
    wavespeed_key: str = ""
    openrouter_key: str = ""


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[str, Path, JobRequest, UserContext]] = asyncio.Queue()
        self._jobs: Dict[str, JobInfo] = {}
        self._cancel_flags: Dict[str, bool] = {}
        self._user_ids: Dict[str, int] = {}
        self._worker_task: Optional[asyncio.Task] = None

    # ----- persist -----
    def _state_path(self, job_id: str) -> Path:
        return settings.jobs_dir / job_id / "state.json"

    def _persist(self, job_id: str) -> None:
        info = self._jobs.get(job_id)
        if not info:
            return
        p = self._state_path(job_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(info.model_dump_json(indent=2), encoding="utf-8")

    def load_from_disk(self) -> None:
        if not settings.jobs_dir.exists():
            return
        import shutil as _sh
        for d in sorted(settings.jobs_dir.iterdir()):
            sp = d / "state.json"
            if not sp.exists():
                continue
            try:
                info = JobInfo.model_validate_json(sp.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[queue] failed to load {sp}: {e}")
                continue
            # завершённые с ошибкой/отменой — стираем при старте (история не копится)
            if info.status in (JobStatus.error, JobStatus.cancelled):
                try: _sh.rmtree(d, ignore_errors=True)
                except Exception: pass
                continue
            # незавершённые (был рестарт во время работы) — тоже стираем
            if info.status not in (JobStatus.done,):
                try: _sh.rmtree(d, ignore_errors=True)
                except Exception: pass
                continue
            self._jobs[info.id] = info

    # ----- worker -----
    def _ensure_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def submit(
        self,
        job_id: str,
        audio_path: Path,
        req: JobRequest,
        user_ctx: Optional[UserContext] = None,
    ) -> JobInfo:
        now = time.time()
        info = JobInfo(
            id=job_id, status=JobStatus.queued, message="в очереди",
            created_at=now, updated_at=now,
        )
        self._jobs[job_id] = info
        ctx = user_ctx or UserContext()
        if ctx.user_id:
            self._user_ids[job_id] = ctx.user_id
        self._persist(job_id)
        await self._queue.put((job_id, audio_path, req, ctx))
        self._ensure_worker()
        return info

    def get(self, job_id: str) -> Optional[JobInfo]:
        return self._jobs.get(job_id)

    def list(self, user_id: Optional[int] = None) -> list[JobInfo]:
        if user_id is None:
            return list(self._jobs.values())
        out: list[JobInfo] = []
        for jid, info in self._jobs.items():
            owner = self._user_ids.get(jid)
            if owner is None or owner == user_id:
                out.append(info)
        return out

    def owner_of(self, job_id: str) -> Optional[int]:
        return self._user_ids.get(job_id)

    def cancel(self, job_id: str) -> bool:
        if job_id not in self._jobs:
            return False
        info = self._jobs[job_id]
        if info.status in (JobStatus.done, JobStatus.error, JobStatus.cancelled):
            return False
        self._cancel_flags[job_id] = True
        # сразу прерываем активную генерацию ComfyUI и чистим очередь
        try:
            import asyncio as _aio
            from ..generators import comfyui_client as _cc
            _aio.get_event_loop().create_task(_cc.interrupt_all())
        except Exception:
            pass
        return True

    def is_cancelled(self, job_id: str) -> bool:
        return self._cancel_flags.get(job_id, False)

    def clear_finished(self) -> int:
        import shutil as _sh
        finished = [jid for jid, info in self._jobs.items()
                    if info.status in (JobStatus.done, JobStatus.error, JobStatus.cancelled)]
        for jid in finished:
            self._jobs.pop(jid, None)
            self._cancel_flags.pop(jid, None)
            d = settings.jobs_dir / jid
            try: _sh.rmtree(d, ignore_errors=True)
            except Exception: pass
        return len(finished)

    def _update(self, job_id: str, **kw) -> None:
        info = self._jobs.get(job_id)
        if not info:
            return
        for k, v in kw.items():
            setattr(info, k, v)
        info.updated_at = time.time()
        self._persist(job_id)

    async def _worker(self) -> None:
        while True:
            job_id, audio_path, req, user_ctx = await self._queue.get()
            try:
                await runner.run_pipeline(
                    job_id, audio_path, req,
                    progress=lambda **kw: self._update(job_id, **kw),
                    cancel_check=lambda: self.is_cancelled(job_id),
                    user_ctx=user_ctx,
                )
            except CancelledError:
                self._update(
                    job_id,
                    status=JobStatus.cancelled,
                    message="отменено",
                    error="cancelled by user",
                )
            except Exception as e:
                # ComfyCancelled -> тоже как cancel
                if e.__class__.__name__ == "ComfyCancelled":
                    self._update(
                        job_id,
                        status=JobStatus.cancelled,
                        message="отменено",
                        error="cancelled by user",
                    )
                    continue
                tb = traceback.format_exc()
                if len(tb) > 2400:
                    tb_view = tb[:1200] + "\n... <traceback trimmed> ...\n" + tb[-1200:]
                else:
                    tb_view = tb
                self._update(
                    job_id,
                    status=JobStatus.error,
                    error=f"{e}\n\n{tb_view}",
                    message="ошибка",
                )
            finally:
                self._cancel_flags.pop(job_id, None)
                self._queue.task_done()


job_queue = JobQueue()
