import os
import sys
import threading
from typing import List, Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager
from pathlib import Path
import time
import numpy as np

# Fix paths for imports
base_dir = Path(__file__).parent.absolute()
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import io
import json
import soundfile as sf
from kokoro_onnx import Kokoro

# Storage paths
userdata_dir = Path(__file__).parent.parent / "userdata"
library_file = userdata_dir / "library.json"
content_dir = userdata_dir / "content"

# Ensure dirs exist
userdata_dir.mkdir(exist_ok=True)
content_dir.mkdir(exist_ok=True)

if not library_file.exists():
    with open(library_file, "w") as f:
        json.dump([], f)

class LibraryItem(BaseModel):
    id: str
    fileName: str
    totalPages: int
    currentPage: int
    lastSentenceIndex: int
    lastAccessed: float

class ContentItem(BaseModel):
    id: str
    pages: List[str]

# Import logic
try:
    from logic.text_normalizer import apply_custom_pronunciations
    from logic.downloader import download_kokoro_model
except ImportError:
    # Fallback for different run environments
    sys.path.append(str(base_dir / "logic"))
    from text_normalizer import apply_custom_pronunciations
    from downloader import download_kokoro_model

# Global engine and status
kokoro = None
system_status = {
    "is_loading": False,
    "last_error": None,
    "progress": 0,
    "is_downloading": False
}

class PatchedKokoro(Kokoro):
    def _create_audio(self, phonemes: str, voice: np.ndarray, speed: float):
        from kokoro_onnx import MAX_PHONEME_LENGTH, SAMPLE_RATE
        phonemes = phonemes[:MAX_PHONEME_LENGTH]
        tokens = np.array(self.tokenizer.tokenize(phonemes), dtype=np.int64)
        voice_style = voice[len(tokens)]
        tokens = [[0, *tokens, 0]]
        inputs = {
            "input_ids": tokens,
            "style": np.array(voice_style, dtype=np.float32),
            "speed": np.array([speed], dtype=np.float32), 
        }
        audio = self.sess.run(None, inputs)[0]
        return audio, SAMPLE_RATE

def load_engine():
    global kokoro, system_status
    system_status["is_loading"] = True
    models_dir = base_dir / "models"
    model_path = models_dir / "kokoro.onnx"
    voices_path = models_dir / "voices.bin"
    
    if model_path.exists() and voices_path.exists():
        try:
            kokoro = PatchedKokoro(str(model_path), str(voices_path))
            system_status["last_error"] = None
        except Exception as e:
            system_status["last_error"] = str(e)
    else:
        system_status["last_error"] = "Models missing"
    
    system_status["is_loading"] = False

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Start engine load in background to not block startup
    threading.Thread(target=load_engine, daemon=True).start()
    yield

app = FastAPI(title="LocalReader Pro API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PronunciationRule(BaseModel):
    id: str
    original: str
    replacement: str
    match_case: bool
    word_boundary: bool

class SynthesisRequest(BaseModel):
    text: str
    voice: str = "af_sky"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []

@app.get("/")
async def serve_ui():
    ui_path = base_dir / "ui" / "index.html"
    return FileResponse(ui_path)

@app.get("/api/library")
async def get_library():
    with open(library_file, "r") as f:
        return json.load(f)

@app.post("/api/library")
async def save_library_item(item: LibraryItem):
    with open(library_file, "r") as f:
        library = json.load(f)
    
    # Update or add
    found = False
    for i, existing in enumerate(library):
        if existing["id"] == item.id:
            library[i] = item.model_dump()
            found = True
            break
    if not found:
        library.append(item.model_dump())
    
    with open(library_file, "w") as f:
        json.dump(library, f)
    return {"status": "ok"}

@app.get("/api/library/content/{doc_id}")
async def get_content(doc_id: str):
    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404)
    with open(file_path, "r") as f:
        return json.load(f)

@app.post("/api/library/content")
async def save_content(item: ContentItem):
    file_path = content_dir / f"{item.id}.json"
    with open(file_path, "w") as f:
        json.dump(item.model_dump(), f)
    return {"status": "ok"}

@app.delete("/api/library/{doc_id}")
async def delete_library_item(doc_id: str):
    # 1. Update library.json
    with open(library_file, "r") as f:
        library = json.load(f)
    
    library = [item for item in library if item["id"] != doc_id]
    
    with open(library_file, "w") as f:
        json.dump(library, f)
    
    # 2. Delete content file
    content_file = content_dir / f"{doc_id}.json"
    if content_file.exists():
        content_file.unlink()
        
    return {"status": "ok"}

@app.get("/api/system/status")
async def get_status():
    return {
        "model_loaded": kokoro is not None,
        "is_loading": system_status["is_loading"],
        "is_downloading": system_status["is_downloading"],
        "last_error": system_status["last_error"],
        "voices": kokoro.get_voices() if kokoro else []
    }

@app.post("/api/system/setup")
async def run_setup(background_tasks: BackgroundTasks):
    global system_status
    if system_status["is_downloading"]:
        return {"status": "already_running"}
    
    def setup_task():
        global system_status
        system_status["is_downloading"] = True
        try:
            download_kokoro_model()
            load_engine() # Try loading after download
        except Exception as e:
            system_status["last_error"] = str(e)
        finally:
            system_status["is_downloading"] = False

    background_tasks.add_task(setup_task)
    return {"status": "started"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/synthesize")
async def synthesize(request: SynthesisRequest):
    if kokoro is None:
        raise HTTPException(status_code=503, detail="TTS Engine is not initialized.")

    try:
        rules_data = [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in request.rules]
        text = apply_custom_pronunciations(request.text, rules_data, request.ignore_list)
    except Exception as e:
        text = request.text

    try:
        voices = kokoro.get_voices()
        selected_voice = request.voice if request.voice in voices else "af_sky"
        if not text.strip(): raise ValueError("Input text is empty")

        samples, sample_rate = kokoro.create(text, voice=selected_voice, speed=float(request.speed or 1.0), lang="en-us")
        flat_samples = samples.flatten()
        
        buffer = io.BytesIO()
        sf.write(buffer, flat_samples, sample_rate, format='WAV', subtype='PCM_16')
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
