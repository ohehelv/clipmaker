"""Композиция итогового клипа через ffmpeg."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import List

from ..config import settings
from ..schemas import Scene


async def probe_duration(path: Path) -> float:
    try:
        proc = await asyncio.create_subprocess_exec(
            settings.ffprobe_bin,
            "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            f"ffprobe не найден: {settings.ffprobe_bin}. "
            "Для Docker укажите FFPROBE_BIN=ffprobe."
        ) from e
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {err.decode(errors='ignore')}")
    return float(out.decode().strip())


async def _run(*args: str) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError as e:
        bin_name = args[0] if args else settings.ffmpeg_bin
        raise RuntimeError(
            f"ffmpeg бинарь не найден: {bin_name}. "
            "Для Docker укажите FFMPEG_BIN=ffmpeg и FFPROBE_BIN=ffprobe."
        ) from e
    _out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(args[:3])}: {err.decode(errors='ignore')[-500:]}")


def _scenes_to_srt(scenes: List[Scene]) -> str:
    def fmt(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines: list[str] = []
    for i, sc in enumerate(scenes, 1):
        if not sc.text:
            continue
        lines.append(str(i))
        lines.append(f"{fmt(sc.start)} --> {fmt(sc.end)}")
        lines.append(sc.text)
        lines.append("")
    return "\n".join(lines)


async def compose(
    scene_videos: list[Path],
    audio_path: Path,
    output_path: Path,
    scenes: List[Scene],
    burn_subtitles: bool = False,
    fps: int = 24,
) -> None:
    """Склейка: concat сцен + наложение аудио. Опционально вшитые субтитры."""
    work = output_path.parent
    list_file = work / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in scene_videos),
        encoding="utf-8",
    )

    concat_video = work / "concat.mp4"
    await _run(
        settings.ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-preset", "medium", "-crf", "20",
        str(concat_video),
    )

    args = [
        settings.ffmpeg_bin, "-y",
        "-i", str(concat_video),
        "-i", str(audio_path),
    ]
    if burn_subtitles:
        srt = work / "subs.srt"
        srt.write_text(_scenes_to_srt(scenes), encoding="utf-8")
        # ffmpeg subtitles filter требует экранирование на Windows
        srt_path = str(srt).replace("\\", "/").replace(":", r"\:")
        args += ["-vf", f"subtitles='{srt_path}'"]
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    else:
        args += ["-c:v", "copy"]
    args += [
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]
    await _run(*args)
