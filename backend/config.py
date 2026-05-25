from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ComfyUI
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_autostart: bool = True
    comfyui_path: Path = Path("./vendor/ComfyUI")
    comfyui_port: int = 8188

    # HF
    hf_token: str = ""

    # Whisper
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    data_dir: Path = Path("./data")

    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    # Видео по умолчанию (Wan 2.2 native — 832x480 @16fps быстро и стабильно)
    default_generator: str = "wan"
    default_width: int = 832
    default_height: int = 480
    default_fps: int = 16

    # Длительность сцены, секунды
    scene_min: float = 6.0
    scene_max: float = 12.0
    scene_target: float = 8.0

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    def ensure_dirs(self) -> None:
        for p in (self.uploads_dir, self.jobs_dir, self.outputs_dir):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
