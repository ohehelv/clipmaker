from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass
class GenRequest:
    prompt: str
    duration: float
    width: int
    height: int
    fps: int
    out_path: Path           # путь, куда генератор должен записать mp4
    work_dir: Path           # рабочая директория сцены
    cancel_check: Optional[Callable[[], bool]] = None


class VideoGenerator(ABC):
    name: str = "base"
    title: str = "Base"
    description: str = ""

    async def is_available(self) -> bool:
        return True

    @abstractmethod
    async def generate(self, req: GenRequest) -> Path:
        """Сгенерировать видео по запросу. Вернуть путь к итоговому mp4."""
        raise NotImplementedError
