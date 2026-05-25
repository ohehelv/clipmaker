"""Заглушка-генератор: цветной плейсхолдер нужной длительности через ffmpeg.

Полезен для отладки пайплайна без GPU/ComfyUI.
"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
from pathlib import Path

from ..config import settings
from .base import GenRequest, VideoGenerator


def _color_from_text(text: str) -> str:
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    return f"0x{h[:6]}"


class StubGenerator(VideoGenerator):
    name = "stub"
    title = "Stub (ffmpeg placeholder)"
    description = "Цветной кадр с подписью промта для теста пайплайна без GPU."

    async def generate(self, req: GenRequest) -> Path:
        req.out_path.parent.mkdir(parents=True, exist_ok=True)
        color = _color_from_text(req.prompt)
        # экранируем текст для drawtext
        safe_text = req.prompt.replace("\\", "/").replace(":", " ").replace("'", " ")[:120]
        vf = (
            f"drawtext=text='{safe_text}':"
            f"fontcolor=white:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.4:boxborderw=10"
        )
        proc = await asyncio.create_subprocess_exec(
            settings.ffmpeg_bin, "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={req.width}x{req.height}:r={req.fps}:d={req.duration:.3f}",
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            str(req.out_path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        _o, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"stub ffmpeg failed: {err.decode(errors='ignore')[-400:]}")
        return req.out_path
