from __future__ import annotations

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class SceneMode(str, Enum):
    whisper = "whisper"   # выравнивание лирики по таймкодам
    llm = "llm"           # LLM-режиссёр
    uniform = "uniform"   # равные сегменты
    single = "single"     # один длинный кадр


class JobStatus(str, Enum):
    queued = "queued"
    aligning = "aligning"
    planning = "planning"
    generating = "generating"
    composing = "composing"
    done = "done"
    error = "error"
    cancelled = "cancelled"


class Scene(BaseModel):
    index: int
    start: float
    end: float
    text: str = ""            # строка лирики/субтитра, если есть
    prompt: str               # итоговый промт для видеогенератора

    @property
    def duration(self) -> float:
        return max(0.1, self.end - self.start)


class JobRequest(BaseModel):
    prompt: str = Field(..., description="Общий стиль/идея клипа")
    lyrics: str = Field("", description="Текст песни (по строкам)")
    scene_mode: SceneMode = SceneMode.whisper
    generator: str = Field("wan5b", description="Имя видеогенератора")
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    n_scenes: int = Field(0, ge=0, le=400, description="0 = авто по длительности")
    burn_subtitles: bool = False
    language: Optional[str] = None  # для Whisper, например 'ru'
    llm_detail: bool = True  # всегда детализировать промты через LLM, если возможно


class JobInfo(BaseModel):
    id: str
    status: JobStatus
    message: str = ""
    progress: float = 0.0
    scenes: List[Scene] = []
    output_url: Optional[str] = None
    error: Optional[str] = None
    eta_seconds: Optional[float] = None
    created_at: float = 0.0
    updated_at: float = 0.0


class GeneratorInfo(BaseModel):
    name: str
    title: str
    description: str = ""
    available: bool = True
