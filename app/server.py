import os
import sys
import threading
from typing import List, Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
import io
import json
import re
import soundfile as sf
import ebooklib
from ebooklib import epub
from xhtml2pdf import pisa
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kokoro_onnx import Kokoro, MAX_PHONEME_LENGTH, SAMPLE_RATE

# Fix paths for imports
base_dir = Path(__file__).parent.absolute()
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

# Storage paths - ENSURE EVERYTHING IS IN THE PROJECT FOLDER
userdata_dir = Path(__file__).parent.parent / "userdata"
library_file = userdata_dir / "library.json"
content_dir = userdata_dir / "content"
settings_file = userdata_dir / "settings.json"

# Ensure dirs exist
userdata_dir.mkdir(exist_ok=True)
content_dir.mkdir(exist_ok=True)

def safe_init_json(path: Path, default_data: Any):
    if not path.exists():
        with open(path, "w") as f:
            json.dump(default_data, f)

safe_init_json(settings_file, {
    "pronunciationRules": [], 
    "ignoreList": [],
    "voice_id": "af_bella",
    "speed": 1.0
})

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

class PronunciationRule(BaseModel):
    id: str
    original: str
    replacement: str
    match_case: bool
    word_boundary: bool

class AppSettings(BaseModel):
    pronunciationRules: List[PronunciationRule]
    ignoreList: List[str]
    voice_id: Optional[str] = "af_bella"
    speed: Optional[float] = 1.0

# Import logic
try:
    from logic.text_normalizer import apply_custom_pronunciations
    from logic.downloader import download_kokoro_model
except ImportError:
    sys.path.append(str(base_dir / "logic"))
    from text_normalizer import apply_custom_pronunciations
    from downloader import download_kokoro_model

# Global engine
kokoro = None
system_status = {"is_loading": False, "last_error": None, "is_downloading": False}

class PatchedKokoro(Kokoro):
    def _create_audio(self, phonemes: str, voice: np.ndarray, speed: float):
        phonemes = phonemes[:MAX_PHONEME_LENGTH]
        tokens = np.array(self.tokenizer.tokenize(phonemes), dtype=np.int64)
        voice_style = voice[len(tokens)]
        tokens = [[0, *tokens, 0]]
        inputs = {"input_ids": tokens, "style": np.array(voice_style, dtype=np.float32), "speed": np.array([speed], dtype=np.float32)}
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
    threading.Thread(target=load_engine, daemon=True).start()
    yield

app = FastAPI(title="LocalReader Pro v1.3 API", lifespan=lifespan)

# Mount local lib folder for self-hosted dependencies
ui_lib_path = base_dir / "ui" / "lib"
if ui_lib_path.exists():
    app.mount("/lib", StaticFiles(directory=str(ui_lib_path)), name="lib")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def serve_ui():
    return FileResponse(base_dir / "ui" / "index.html")

# Settings API (Rules & Ignore)
@app.get("/api/settings")
async def get_settings():
    with open(settings_file, "r") as f:
        return json.load(f)

def safe_save_json(path: Path, data: Any):
    # Atomic write to prevent corruption
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        json.dump(data, f)
    temp_path.replace(path)

@app.post("/api/settings")
async def save_settings(settings: AppSettings):
    safe_save_json(settings_file, settings.model_dump())
    return {"status": "ok"}

# Library API
@app.post("/api/convert/epub")
async def convert_epub(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="Not an EPUB file")
    
    temp_epub = content_dir / f"temp_{os.getpid()}.epub"
    temp_pdf = content_dir / f"converted_{os.getpid()}.pdf"
    
    try:
        with open(temp_epub, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Check for DRM (very basic check: ebooklib will throw if it can't parse)
        try:
            book = epub.read_epub(str(temp_epub))
        except Exception:
            raise HTTPException(status_code=400, detail="Cannot read protected file (DRM)")

        html_content = "<html><body>"
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                body = soup.find('body')
                if body:
                    html_content += str(body)
                else:
                    html_content += str(soup)
        html_content += "</body></html>"
        
        # Convert to PDF
        with open(temp_pdf, "wb") as f:
            pisa_status = pisa.CreatePDF(html_content, dest=f)
        
        if pisa_status.err:
            raise HTTPException(status_code=500, detail="PDF conversion failed")
            
        return FileResponse(temp_pdf, media_type="application/pdf", filename=temp_pdf.name)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_epub.exists(): temp_epub.unlink()
        # Note: We keep the PDF for a bit or until next conversion? 
        # Actually, the user's browser will download it. 
        # We should probably delete it after response is sent if we want to be clean.
        # But for now, we leave it in userdata/content as requested by spec.

@app.get("/api/library")
async def get_library():
    try:
        with open(library_file, "r") as f:
            return json.load(f)
    except Exception: return []

@app.post("/api/library")
async def save_library_item(item: LibraryItem):
    try:
        with open(library_file, "r") as f:
            library = json.load(f)
    except Exception: library = []
    
    found = False
    for i, existing in enumerate(library):
        if existing.get("id") == item.id:
            library[i] = item.model_dump()
            found = True
            break
    if not found: library.append(item.model_dump())
    
    safe_save_json(library_file, library)
    return {"status": "ok"}

@app.get("/api/library/content/{doc_id}")
async def get_content(doc_id: str):
    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists(): raise HTTPException(status_code=404)
    with open(file_path, "r") as f:
        return json.load(f)

@app.post("/api/library/content")
async def save_content(item: ContentItem):
    safe_save_json(content_dir / f"{item.id}.json", item.model_dump())
    return {"status": "ok"}

@app.delete("/api/library/{doc_id}")
async def delete_library_item(doc_id: str):
    try:
        with open(library_file, "r") as f:
            library = json.load(f)
        library = [i for i in library if i.get("id") != doc_id]
        safe_save_json(library_file, library)
    except Exception: pass
    
    content_file = content_dir / f"{doc_id}.json"
    if content_file.exists(): content_file.unlink()
    return {"status": "ok"}

# System API
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
    if system_status["is_downloading"]: return {"status": "already_running"}
    def setup_task():
        system_status["is_downloading"] = True
        try:
            download_kokoro_model()
            load_engine()
        except Exception as e: system_status["last_error"] = str(e)
        finally: system_status["is_downloading"] = False
    background_tasks.add_task(setup_task)
    return {"status": "started"}

class SynthesisRequest(BaseModel):
    text: str
    voice: str = "af_sky"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []

@app.post("/api/synthesize")
async def synthesize(request: SynthesisRequest):
    if kokoro is None: raise HTTPException(status_code=503, detail="TTS Engine not initialized.")
    try:
        rules_data = [r.model_dump() for r in request.rules]
        text = apply_custom_pronunciations(request.text, rules_data, request.ignore_list)
    except Exception: text = request.text
    try:
        voices = kokoro.get_voices()
        selected_voice = request.voice if request.voice in voices else "af_sky"
        
        # Heuristic: If text has no alphanumeric characters, return tiny silence
        if not re.search(r'[a-zA-Z0-9]', text):
            # 0.1s silence
            samples = np.zeros(int(24000 * 0.1), dtype=np.float32)
            sample_rate = 24000
        else:
            samples, sample_rate = kokoro.create(text, voice=selected_voice, speed=float(request.speed or 1.0), lang="en-us")
        
        buffer = io.BytesIO()
        sf.write(buffer, samples.flatten(), sample_rate, format='WAV', subtype='PCM_16')
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="audio/wav")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
