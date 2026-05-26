"""Полный пайплайн задачи: probe → align/plan → generate per-scene → compose.
Поддержка cancel, retry на сцене, ETA.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Callable, List

from ..config import settings
from ..core import compose
from ..core.scenes import plan_scenes
from ..generators import registry
from ..generators.base import GenRequest
from ..schemas import JobRequest, JobStatus, Scene


Progress = Callable[..., None]
CancelCheck = Callable[[], bool]


def _check_cancel(cancel_check: CancelCheck) -> None:
    if cancel_check():
        # импортируем тут, чтобы избежать циклов
        from .queue import CancelledError
        raise CancelledError()


async def run_pipeline(
    job_id: str,
    audio_path: Path,
    req: JobRequest,
    progress: Progress,
    cancel_check: CancelCheck,
) -> None:
    job_dir = settings.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir = job_dir / "scenes"
    scenes_dir.mkdir(exist_ok=True)

    progress(status=JobStatus.aligning, message="анализ аудио", progress=0.02)
    duration = await compose.probe_duration(audio_path)
    _check_cancel(cancel_check)

    progress(status=JobStatus.planning, message="планирование сцен", progress=0.08)
    scenes: List[Scene] = await plan_scenes(req, audio_path, duration)
    progress(scenes=scenes, progress=0.15)
    _check_cancel(cancel_check)

    (job_dir / "scenes.json").write_text(
        "[" + ",\n".join(s.model_dump_json() for s in scenes) + "]",
        encoding="utf-8",
    )

    width = req.width or settings.default_width
    height = req.height or settings.default_height
    fps = req.fps or settings.default_fps

    gen = registry.get(req.generator)

    progress(status=JobStatus.generating, message=f"генерация ({req.generator})", progress=0.18)
    scene_videos: list[Path] = []
    total = len(scenes)
    t_gen_start = time.time()

    avg_scene: float = 0.0  # средняя длительность по уже готовым сценам

    async def _heartbeat(scene_idx: int, t_scene_start: float) -> None:
        """Каждые 5 сек обновляем сообщение и под-прогресс текущей сцены."""
        try:
            while True:
                await asyncio.sleep(5.0)
                el = time.time() - t_scene_start
                mm, ss = divmod(int(el), 60)
                # оценка под-прогресса по среднему предыдущих сцен (cap 0.95)
                if avg_scene > 0:
                    sub = min(0.95, el / avg_scene)
                else:
                    sub = 0.0
                base = 0.18 + 0.72 * scene_idx / max(1, total)
                step = 0.72 / max(1, total)
                progress(
                    progress=base + step * sub,
                    message=f"сцена {scene_idx + 1}/{total} — {mm:02d}:{ss:02d}",
                )
        except asyncio.CancelledError:
            return

    for i, sc in enumerate(scenes):
        _check_cancel(cancel_check)
        out = scenes_dir / f"scene_{i:04d}.mp4"
        greq = GenRequest(
            prompt=sc.prompt,
            duration=sc.duration,
            width=width,
            height=height,
            fps=fps,
            out_path=out,
            work_dir=scenes_dir,
            cancel_check=cancel_check,
        )
        t_scene_start = time.time()
        hb_task = asyncio.create_task(_heartbeat(i, t_scene_start))
        # retry до 2 раз
        last_exc: Exception | None = None
        try:
            for attempt in range(2):
                try:
                    await gen.generate(greq)
                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    await asyncio.sleep(1.0)
        finally:
            hb_task.cancel()
            try:
                await hb_task
            except asyncio.CancelledError:
                pass
        if last_exc is not None:
            raise last_exc
        scene_videos.append(out)

        done = i + 1
        # ETA
        elapsed = time.time() - t_gen_start
        avg_scene = elapsed / done
        remaining = avg_scene * (total - done)
        progress(
            progress=0.18 + 0.72 * done / max(1, total),
            message=f"сцена {done}/{total} готова (среднее {avg_scene:.0f}с)",
            eta_seconds=remaining,
        )

    _check_cancel(cancel_check)
    progress(status=JobStatus.composing, message="склейка", progress=0.92, eta_seconds=None)
    out_path = settings.outputs_dir / f"{job_id}.mp4"
    await compose.compose(
        scene_videos=scene_videos,
        audio_path=audio_path,
        output_path=out_path,
        scenes=scenes,
        burn_subtitles=req.burn_subtitles,
        fps=fps,
    )

    rel = out_path.relative_to(settings.data_dir).as_posix()
    progress(
        status=JobStatus.done,
        progress=1.0,
        message="готово",
        output_url=f"/files/{rel}",
    )
