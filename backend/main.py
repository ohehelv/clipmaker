from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .api import jobs as jobs_api
from .api import models as models_api
from .api import health as health_api
from .api import prompts as prompts_api
from .api import auth as auth_api
from .api import settings as settings_api
from .db.session import init_db
from .jobs.queue import job_queue
from .services import comfyui_lifecycle


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    job_queue.load_from_disk()
    try:
        await comfyui_lifecycle.start_if_needed()
    except Exception as e:
        print(f"[lifespan] ComfyUI autostart failed: {e}")
    yield
    await comfyui_lifecycle.shutdown()


app = FastAPI(title="ClipMaker", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth — без авторизации (сами являются входной точкой).
app.include_router(auth_api.router, prefix="/api/auth", tags=["auth"])
# Остальное — авторизация внутри эндпоинтов (Depends(get_current_user)).
app.include_router(jobs_api.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(models_api.router, prefix="/api/models", tags=["models"])
app.include_router(prompts_api.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(health_api.router, prefix="/api/health", tags=["health"])

# отдача готовых файлов
app.mount("/files", StaticFiles(directory=str(settings.data_dir)), name="files")

# статика фронта
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        # Отдаём конкретный html если он есть, иначе index.html (SPA).
        target = FRONTEND_DIR / path
        if target.is_file():
            return FileResponse(target)
        html = FRONTEND_DIR / f"{path}.html"
        if html.is_file():
            return FileResponse(html)
        return FileResponse(FRONTEND_DIR / "index.html")
