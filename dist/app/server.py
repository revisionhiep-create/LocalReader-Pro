from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import json
import psutil

# Import Refactored Modules
from .config import (
    base_dir,
    userdata_dir,
    content_dir,
    settings_file,
    library_file,
)
from .utils import safe_save_json, safe_init_json
import app.state as state_module
from .routers import settings, library, tts, system, export, timer
from .utils import safe_init_json


# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    start_time = time.time()

    # 1. Check directories
    if not base_dir.exists():
        print(f"[CRITICAL] Base dir missing: {base_dir}")

    # 2. Init JSON files
    safe_init_json(
        settings_file,
        {
            "pronunciationRules": [],
            "ignoreList": [],
            "voice_id": "af_bella",
            "speed": 1.0,
            "engine_mode": "gpu",
            "ui_language": "en",
        },
    )
    safe_init_json(library_file, [])

    # 3. Check/Install FFMPEG (Async check could go here)
    # We leave that for the frontend to query via /api/ffmpeg/status

    # 4. Clean temp content
    try:
        if content_dir.exists():
            for f in content_dir.glob("temp_*"):
                try:
                    f.unlink()
                except:
                    pass
    except Exception as e:
        print(f"[STARTUP] Cleanup warning: {e}")

    # 5. Load model (Auto-load on startup)
    try:
        from .routers.system import load_engine_logic

        print("[STARTUP] Checking for existing models to auto-load...")
        load_engine_logic()
    except Exception as e:
        print(f"[STARTUP] Auto-load failed (non-critical): {e}")

    print(f"[STARTUP] Server ready in {time.time() - start_time:.2f}s")

    yield

    # Shutdown logic
    state_module.sleep_timer.stop_timer()
    print("[SHUTDOWN] Cleanup complete.")


# --- App Definition ---
app = FastAPI(lifespan=lifespan)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(settings.router)
app.include_router(library.router)
app.include_router(tts.router)
app.include_router(system.router)
app.include_router(export.router)
app.include_router(timer.router)

# --- Static Files ---
# Mount static assets
ui_dir = base_dir / "ui"
if ui_dir.exists():
    app.mount("/css", StaticFiles(directory=ui_dir / "css"), name="css")
    app.mount("/js", StaticFiles(directory=ui_dir / "js"), name="js")
    if (ui_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=ui_dir / "assets"), name="assets")
    app.mount("/locales", StaticFiles(directory=base_dir / "locales"), name="locales")
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
else:
    print(f"[WARNING] UI directory not found: {ui_dir}")


# --- Legacy/Root Endpoints ---
@app.get("/health")
async def health_check():
    process = psutil.Process()
    return {"status": "ok", "memory_mb": process.memory_info().rss / 1024 / 1024}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
