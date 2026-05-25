from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .api import jobs as jobs_api
from .api import models as models_api
from .api import prompts as prompts_api
from .api.security import require_api_key
from .jobs.queue import job_queue
from .services import comfyui_lifecycle


@asynccontextmanager
async def lifespan(app: FastAPI):
    job_queue.load_from_disk()
    try:
        await comfyui_lifecycle.start_if_needed()
    except Exception as e:
        print(f"[lifespan] ComfyUI autostart failed: {e}")
    yield
    await comfyui_lifecycle.shutdown()


app = FastAPI(title="ClipMaker", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_api.router, prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(require_api_key)])
app.include_router(models_api.router, prefix="/api/models", tags=["models"], dependencies=[Depends(require_api_key)])
app.include_router(prompts_api.router, prefix="/api/prompts", tags=["prompts"], dependencies=[Depends(require_api_key)])

# отдача готовых файлов
app.mount("/files", StaticFiles(directory=str(settings.data_dir)), name="files")

# статика фронта
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")
