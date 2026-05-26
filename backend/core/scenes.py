"""Планирование сцен клипа в 4 режимах + smart-defaults."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import List

from ..config import settings
from ..schemas import JobRequest, Scene, SceneMode
from . import llm as llm_client
from .alignment import LyricLine, align_lyrics
from .prompts_store import get_prompts


def _detail_prompt_fallback(base: str, line: str) -> str:
    if line:
        return f"{base}. Scene: {line}".strip()
    return base


async def _detail_prompt(base: str, line: str, use_llm: bool, openrouter_key: str | None = None) -> str:
    has_key = bool((openrouter_key or settings.openrouter_api_key))
    if not use_llm or not has_key:
        return _detail_prompt_fallback(base, line)
    try:
        user = f"General concept: {base}\nLyric line: {line or '(instrumental)'}"
        return (await llm_client.chat(
            get_prompts()["detail_system"], user,
            api_key=openrouter_key, temperature=0.8,
        )).strip()
    except llm_client.LLMError:
        return _detail_prompt_fallback(base, line)


def _auto_n_scenes(duration: float) -> int:
    return max(1, math.ceil(duration / settings.scene_target))


def _clamp_lines(lines: List[LyricLine], duration: float) -> List[LyricLine]:
    """Слить короткие сцены, разбить длинные."""
    if not lines:
        return lines
    mn, mx = settings.scene_min, settings.scene_max

    changed = True
    while changed and len(lines) > 1:
        changed = False
        for i, ln in enumerate(lines):
            if (ln.end - ln.start) >= mn:
                continue
            if i == 0:
                lines[1].start = ln.start
                lines[1].text = (ln.text + " " + lines[1].text).strip()
                del lines[0]
            elif i == len(lines) - 1:
                lines[-2].end = ln.end
                lines[-2].text = (lines[-2].text + " " + ln.text).strip()
                del lines[-1]
            else:
                left = lines[i - 1]
                right = lines[i + 1]
                if (right.end - right.start) <= (left.end - left.start):
                    right.start = ln.start
                    right.text = (ln.text + " " + right.text).strip()
                else:
                    left.end = ln.end
                    left.text = (left.text + " " + ln.text).strip()
                del lines[i]
            changed = True
            break

    out: list[LyricLine] = []
    for ln in lines:
        dur = ln.end - ln.start
        if dur <= mx:
            out.append(ln)
            continue
        n = math.ceil(dur / mx)
        step = dur / n
        for k in range(n):
            out.append(LyricLine(
                text=ln.text if k == 0 else "",
                start=ln.start + k * step,
                end=ln.start + (k + 1) * step,
            ))
    out[0].start = 0.0
    out[-1].end = duration
    return out


async def plan_uniform(req: JobRequest, duration: float, openrouter_key: str | None = None) -> List[Scene]:
    n = req.n_scenes if req.n_scenes > 0 else _auto_n_scenes(duration)
    step = duration / n
    scenes: list[Scene] = []
    for i in range(n):
        prompt = await _detail_prompt(req.prompt, "", use_llm=req.llm_detail, openrouter_key=openrouter_key)
        scenes.append(Scene(index=i, start=i * step, end=(i + 1) * step, text="", prompt=prompt))
    return scenes


async def plan_single(req: JobRequest, duration: float) -> List[Scene]:
    return [Scene(index=0, start=0.0, end=duration, text="", prompt=req.prompt)]


async def plan_whisper(req: JobRequest, audio_path: Path, duration: float, openrouter_key: str | None = None) -> List[Scene]:
    if not req.lyrics.strip():
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    lines = align_lyrics(audio_path, req.lyrics, language=req.language, audio_duration=duration)
    if not lines:
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    lines = _clamp_lines(lines, duration)
    scenes: list[Scene] = []
    for i, ln in enumerate(lines):
        prompt = await _detail_prompt(req.prompt, ln.text, use_llm=req.llm_detail, openrouter_key=openrouter_key)
        scenes.append(Scene(index=i, start=ln.start, end=ln.end, text=ln.text, prompt=prompt))
    return scenes


_JSON_RE = re.compile(r"\[.*\]", re.S)


async def plan_llm(req: JobRequest, duration: float, openrouter_key: str | None = None) -> List[Scene]:
    has_key = bool((openrouter_key or settings.openrouter_api_key))
    if not has_key:
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    user = (
        f"Duration: {duration:.2f} seconds\n"
        f"Scene target length: {settings.scene_target:.1f}s "
        f"(min {settings.scene_min:.1f}, max {settings.scene_max:.1f})\n"
        f"General prompt: {req.prompt}\n"
        f"Lyrics:\n{req.lyrics or '(no lyrics provided)'}"
    )
    try:
        planner_model = settings.openrouter_planner_model or None
        raw = await llm_client.chat(
            get_prompts()["director_system"], user,
            model=planner_model, api_key=openrouter_key, temperature=0.7,
        )
    except llm_client.LLMError:
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    m = _JSON_RE.search(raw)
    if not m:
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    scenes: list[Scene] = []
    for i, item in enumerate(data):
        scenes.append(Scene(
            index=i,
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item.get("text", "")),
            prompt=str(item["prompt"]),
        ))
    if scenes:
        scenes[0].start = 0.0
        scenes[-1].end = duration
    return scenes


async def plan_scenes(req: JobRequest, audio_path: Path, duration: float, openrouter_key: str | None = None) -> List[Scene]:
    if req.scene_mode == SceneMode.single:
        return await plan_single(req, duration)
    if req.scene_mode == SceneMode.uniform:
        return await plan_uniform(req, duration, openrouter_key=openrouter_key)
    if req.scene_mode == SceneMode.llm:
        return await plan_llm(req, duration, openrouter_key=openrouter_key)
    return await plan_whisper(req, audio_path, duration, openrouter_key=openrouter_key)
