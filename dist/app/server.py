import os
import sys
import threading
import subprocess
from typing import List, Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
import io
import json
import re
import hashlib
import soundfile as sf
import ebooklib
from ebooklib import epub
from xhtml2pdf import pisa
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kokoro_onnx import Kokoro, MAX_PHONEME_LENGTH, SAMPLE_RATE
from pydub import AudioSegment
import time
import platform

# Fix paths for imports
base_dir = Path(__file__).parent.absolute()
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

# CRITICAL: Path Anchoring Functions
# These ensure paths are ALWAYS relative to THIS script file, not the current working directory
def get_app_anchored_path(relative_path: str) -> Path:
    """
    Returns a guaranteed absolute path relative to THIS script file.
    Immune to where the user launched the terminal from.
    
    Args:
        relative_path: Path relative to the app root (e.g., "userdata/file.mp3")
    
    Returns:
        Absolute Path object anchored to the script location
    """
    # Get the app root (parent of this script's directory)
    script_dir = Path(__file__).parent.absolute()  # .../app/
    app_root = script_dir.parent  # .../LocalReader_Pro_v1.4/
    
    # Join and resolve to absolute path
    return (app_root / relative_path).absolute()

# Storage paths - ANCHORED to script location (immune to CWD changes)
userdata_dir = get_app_anchored_path("userdata")
library_file = userdata_dir / "library.json"
content_dir = userdata_dir / "content"
settings_file = userdata_dir / "settings.json"
cache_db_path = userdata_dir / "audio_cache.db"  # SQLite cache database

# Cache Management Settings
MAX_CACHE_SIZE_MB = 200  # Maximum cache size in megabytes (SQLite DB)

# Ensure dirs exist (with clear logging)
try:
    userdata_dir.mkdir(exist_ok=True)
    content_dir.mkdir(exist_ok=True)
    print(f"[OK] Storage initialized at: {userdata_dir}")
    print(f"[OK] Audio cache (SQLite) at: {cache_db_path}")
except Exception as e:
    print(f"[CRITICAL] Failed to create storage dirs: {e}")
    print(f"           Attempted path: {userdata_dir}")

def safe_init_json(path: Path, default_data: Any):
    if not path.exists():
        with open(path, "w") as f:
            json.dump(default_data, f)

safe_init_json(settings_file, {
    "pronunciationRules": [], 
    "ignoreList": [],
    "voice_id": "af_bella",
    "speed": 1.0,
    "header_footer_mode": "off",  # Options: "off", "clean", "dim"
    "engine_mode": "gpu",  # Options: "gpu" (standard), "cpu" (quantized)
    "ui_language": "en",  # Options: "en", "fr", "es"
    "pause_settings": {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 0
    }
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
    is_regex: Optional[bool] = False

class AppSettings(BaseModel):
    pronunciationRules: List[PronunciationRule]
    ignoreList: List[str]
    voice_id: Optional[str] = "af_bella"
    speed: Optional[float] = 1.0
    header_footer_mode: Optional[str] = "off"  # "off", "clean", or "dim"
    engine_mode: Optional[str] = "gpu"  # "gpu" (standard) or "cpu" (quantized)
    ui_language: Optional[str] = "en"  # "en", "fr", or "es"
    pause_settings: Optional[Dict[str, int]] = {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 800
    }

# Import logic
try:
    from logic.text_normalizer import apply_custom_pronunciations, inject_pauses
    from logic.downloader import download_kokoro_model, check_model_exists, get_available_models
    from logic.dependency_manager import FFMPEGInstaller, get_ffmpeg_path, configure_pydub
    from logic.smart_content_detector import find_content_start_page, detect_headers_footers, apply_header_footer_filter, filter_text_for_tts
    from logic.audio_cache import AudioCache
except ImportError:
    sys.path.append(str(base_dir / "logic"))
    from text_normalizer import apply_custom_pronunciations, inject_pauses
    from downloader import download_kokoro_model, check_model_exists, get_available_models
    from dependency_manager import FFMPEGInstaller, get_ffmpeg_path, configure_pydub
    from smart_content_detector import find_content_start_page, detect_headers_footers, apply_header_footer_filter, filter_text_for_tts
    from audio_cache import AudioCache

# Initialize SQLite audio cache
audio_cache = AudioCache(cache_db_path, max_size_mb=MAX_CACHE_SIZE_MB)

# Global engine
kokoro = None
system_status = {"is_loading": False, "last_error": None, "is_downloading": False}
export_status = {"is_exporting": False, "progress": 0, "total": 0, "error": None, "output_file": None}
ffmpeg_status = {"is_installed": False, "is_downloading": False, "progress": 0, "total": 0, "error": None, "message": ""}
ffmpeg_installer = None

class PatchedKokoro(Kokoro):
    """
    Patched version for GPU (FP32) models only.
    GPU models expect 'input_ids' (int64) but kokoro-onnx provides 'tokens'.
    CPU (INT8) models work fine with default Kokoro class.
    """
    def _create_audio(self, phonemes: str, voice: np.ndarray, speed: float):
        phonemes = phonemes[:MAX_PHONEME_LENGTH]
        tokens = np.array(self.tokenizer.tokenize(phonemes), dtype=np.int64)
        voice_style = voice[len(tokens)]
        tokens = [[0, *tokens, 0]]
        inputs = {"input_ids": tokens, "style": np.array(voice_style, dtype=np.float32), "speed": np.array([speed], dtype=np.float32)}
        audio = self.sess.run(None, inputs)[0]
        return audio, SAMPLE_RATE

def load_engine(requested_mode: Optional[str] = None):
    """
    Load TTS engine with dual-model support and automatic fallback.
    
    Args:
        requested_mode: "gpu" or "cpu". If None, reads from settings.json
    """
    global kokoro, system_status
    system_status["is_loading"] = True
    
    # Determine requested mode
    if requested_mode is None:
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
            requested_mode = settings.get("engine_mode", "gpu")
        except Exception:
            requested_mode = "gpu"  # Default fallback
    
    models_dir = base_dir / "models"
    voices_path = models_dir / "voices.bin"
    
    # Define model paths
    gpu_model_path = models_dir / "kokoro.onnx"
    cpu_model_path = models_dir / "kokoro.int8.onnx"
    
    # Select primary and fallback models
    if requested_mode == "cpu":
        primary_model = cpu_model_path
        fallback_model = gpu_model_path
        primary_label = "CPU (Quantized)"
        fallback_label = "GPU (Standard)"
    else:
        primary_model = gpu_model_path
        fallback_model = cpu_model_path
        primary_label = "GPU (Standard)"
        fallback_label = "CPU (Quantized)"
    
    # Check voices first
    if not voices_path.exists():
        system_status["last_error"] = "Voice pack missing. Please run setup."
        system_status["is_loading"] = False
        return
    
    # Try to load primary model
    model_to_load = None
    actual_mode = requested_mode
    
    if primary_model.exists():
        model_to_load = primary_model
        print(f"[ENGINE] Loading {primary_label} model: {primary_model.name}")
    elif fallback_model.exists():
        model_to_load = fallback_model
        actual_mode = "cpu" if requested_mode == "gpu" else "gpu"
        fallback_msg = f"Requested {primary_label} model not found. Using {fallback_label} model instead."
        print(f"[ENGINE] {fallback_msg}")
        system_status["last_error"] = fallback_msg
    else:
        system_status["last_error"] = "No TTS models found. Please run setup."
        system_status["is_loading"] = False
        return
    
    # Load the selected model
    try:
        # CRITICAL: Close old model first if switching
        if kokoro is not None:
            print(f"[ENGINE] Unloading previous model...")
            kokoro = None  # Release old model
        
        print(f"[ENGINE] Initializing {actual_mode.upper()} model...")
        
        # Use PatchedKokoro for GPU (needs input_ids), regular Kokoro for CPU (uses tokens natively)
        if actual_mode == "gpu":
            print(f"[ENGINE] Using PatchedKokoro for GPU model compatibility...")
            kokoro = PatchedKokoro(str(model_to_load), str(voices_path))
        else:
            print(f"[ENGINE] Using default Kokoro for CPU model...")
            kokoro = Kokoro(str(model_to_load), str(voices_path))
        
        # DON'T change user's preference when falling back!
        # Just warn them and keep their selection
        if actual_mode != requested_mode:
            fallback_warning = f"Using {actual_mode.upper()} model (your selected {requested_mode.upper()} model not found)"
            system_status["last_error"] = fallback_warning
            print(f"[ENGINE WARNING] {fallback_warning}")
        else:
            # Clear error only if we loaded the requested model
            system_status["last_error"] = None
        
        print(f"[ENGINE] Successfully loaded {actual_mode.upper()} model")
        print(f"[ENGINE] Model file: {model_to_load.name}")
        print(f"[ENGINE] Available voices: {len(kokoro.get_voices())}")
        
    except Exception as e:
        system_status["last_error"] = f"Failed to load TTS engine: {str(e)}"
        print(f"[ENGINE ERROR] {system_status['last_error']}")
        import traceback
        traceback.print_exc()
    
    system_status["is_loading"] = False

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global ffmpeg_status
    
    # Validate voice model on startup
    print("[STARTUP] Validating TTS models...")
    voices_path = get_app_anchored_path("app/models/voices.bin")
    
    if not voices_path.exists():
        print("[WARNING] voices.bin not found - multilingual voices unavailable")
        print("          Run 'Setup Voice Engine' to download the model")
    else:
        file_size_mb = voices_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Voice model loaded: {file_size_mb:.1f} MB")
        
        if file_size_mb < 25:
            print("[WARNING] Legacy voice model detected (English-only, ~5MB)")
            print("          For French/Spanish support, download multilingual model:")
            print("          https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin")
        else:
            print("[OK] Multilingual voice model detected (26 voices: EN/FR/ES/JP/GB)")
    
    threading.Thread(target=load_engine, daemon=True).start()
    # Check FFMPEG on startup
    installer = FFMPEGInstaller()
    ffmpeg_status["is_installed"] = installer.check_installed()
    
    # Log cache stats on startup
    try:
        cache_count = audio_cache.get_count()
        cache_size = audio_cache.get_size_mb()
        print(f"[CACHE] Initialized: {cache_count} entries, {cache_size:.2f} MB")
    except Exception as e:
        print(f"[CACHE WARNING] Failed to read cache stats: {e}")
    
    yield

app = FastAPI(title="LocalReader Pro API", lifespan=lifespan)

# Mount local lib folder for self-hosted dependencies
ui_lib_path = base_dir / "ui" / "lib"
if ui_lib_path.exists():
    app.mount("/lib", StaticFiles(directory=str(ui_lib_path)), name="lib")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def serve_ui():
    ui_file = base_dir / "ui" / "index.html"
    if not ui_file.exists():
        return JSONResponse(
            status_code=500, 
            content={"error": "UI file missing. Please check installation.", "path": str(ui_file)}
        )
    return FileResponse(ui_file)

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

# Locale API (v2.0 - Multilingual Support)
@app.get("/api/locale/{lang}")
async def get_locale(lang: str):
    """Serve translation JSON for specified language (en, fr, es, zh)"""
    if lang not in ["en", "fr", "es", "zh"]:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")
    
    locale_path = base_dir / "locales" / f"{lang}.json"
    
    if not locale_path.exists():
        raise HTTPException(status_code=404, detail=f"Translation file not found: {lang}.json")
    
    with open(locale_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.get("/api/voices/available")
async def get_available_voices():
    """Return categorized list of available voice IDs based on loaded voice model"""
    voices_path = get_app_anchored_path("app/models/voices.bin")
    
    if not voices_path.exists():
        return {
            "model": "none",
            "voices": {},
            "size_mb": 0
        }
    
    # Check file size to determine model type
    file_size_mb = voices_path.stat().st_size / (1024 * 1024)
    model_type = "multilingual" if file_size_mb > 25 else "english-only"
    
    # Define voice definitions with metadata
    # This acts as the "Source of Truth" for the frontend
    voice_definitions = {
        "en-us": {
            "label": "English (American)",
            "voices": [
                {"id": "af_bella", "name": "AF Bella (Female)"},
                {"id": "af_sky", "name": "AF Sky (Female)"},
                {"id": "af_nicole", "name": "AF Nicole (Female)"},
                {"id": "af_sarah", "name": "AF Sarah (Female)"},
                {"id": "am_adam", "name": "AM Adam (Male)"},
                {"id": "am_michael", "name": "AM Michael (Male)"}
            ]
        },
        "en-gb": {
            "label": "English (British)",
            "voices": [
                {"id": "bf_emma", "name": "BF Emma (Female)"},
                {"id": "bf_isabella", "name": "BF Isabella (Female)"},
                {"id": "bm_george", "name": "BM George (Male)"},
                {"id": "bm_lewis", "name": "BM Lewis (Male)"}
            ]
        },
        "fr-fr": {
            "label": "French",
            "voices": [
                {"id": "ff_siwis", "name": "FF Siwis (Female)"}
            ]
        },
        "es": {
            "label": "Spanish",
            "voices": [
                {"id": "ef_dora", "name": "EF Dora (Female)"},
                {"id": "em_alex", "name": "EM Alex (Male)"},
                {"id": "em_santa", "name": "EM Santa (Male)"}
            ]
        },
        "cmn": {
            "label": "Chinese",
            "voices": [
                {"id": "zf_xiaobei", "name": "ZF Xiaobei (Female)"},
                {"id": "zf_xiaomi", "name": "ZF Xiaomi (Female)"},
                {"id": "zf_xiaoxiao", "name": "ZF Xiaoxiao (Female)"},
                {"id": "zf_xiaoyi", "name": "ZF Xiaoyi (Female)"}
            ]
        },
        "it": {
            "label": "Italian",
            "voices": [
                {"id": "if_sara", "name": "IF Sara (Female)"},
                {"id": "im_nicola", "name": "IM Nicola (Male)"}
            ]
        },
        "pt-br": {
            "label": "Portuguese",
            "voices": [
                {"id": "pf_dora", "name": "PF Dora (Female)"},
                {"id": "pm_alex", "name": "PM Alex (Male)"}
            ]
        }
    }
    
    # Filter voices based on loaded model
    available_categories = {}
    
    if model_type == "multilingual":
        # Return all categories
        available_categories = voice_definitions
    else:
        # Return only English categories for legacy model
        available_categories = {
            "en-us": voice_definitions["en-us"],
            "en-gb": voice_definitions["en-gb"]
        }
        
    return {
        "model": model_type,
        "size_mb": round(file_size_mb, 1),
        "categories": available_categories
    }

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
        data = json.load(f)
    
    # Add smart start page info
    pages = data.get('pages', [])
    if pages:
        smart_start = find_content_start_page(pages)
        data['smart_start_page'] = smart_start
    
    return data

@app.post("/api/library/content")
async def save_content(item: ContentItem):
    safe_save_json(content_dir / f"{item.id}.json", item.model_dump())
    return {"status": "ok"}

@app.get("/api/library/content/{doc_id}/page/{page_index}")
async def get_page_with_filter(doc_id: str, page_index: int):
    """Get a specific page with smart header/footer filtering applied."""
    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    pages = data.get('pages', [])
    if page_index < 0 or page_index >= len(pages):
        raise HTTPException(status_code=400, detail="Invalid page index")
    
    # Load user settings for header/footer mode
    with open(settings_file, "r") as f:
        settings = json.load(f)
    
    mode = settings.get('header_footer_mode', 'off')
    
    # Get the original page text
    page_text = pages[page_index]
    
    # Detect headers/footers
    noise = detect_headers_footers(pages, page_index)
    
    # Apply filter if mode is not "off"
    if mode in ['clean', 'dim']:
        filtered_text = apply_header_footer_filter(
            page_text, 
            noise['headers'], 
            noise['footers'], 
            mode
        )
    else:
        filtered_text = page_text
    
    return {
        "page_index": page_index,
        "original_text": page_text,
        "filtered_text": filtered_text,
        "headers": noise['headers'],
        "footers": noise['footers'],
        "mode": mode
    }

@app.get("/api/library/search/{doc_id}")
async def search_book(doc_id: str, q: str):
    """Search for text across all pages in a document."""
    if not q or len(q) < 2:
        return {"results": [], "total_matches": 0, "query": q}
    
    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    pages = data.get('pages', [])
    query_lower = q.lower()
    results = []
    total_matches = 0
    
    for page_index, page_text in enumerate(pages):
        page_lower = page_text.lower()
        
        # Count occurrences on this page
        match_count = page_lower.count(query_lower)
        
        if match_count > 0:
            # Find all match positions
            matches = []
            start = 0
            while True:
                pos = page_lower.find(query_lower, start)
                if pos == -1:
                    break
                
                # Extract context (50 chars before/after)
                context_start = max(0, pos - 50)
                context_end = min(len(page_text), pos + len(q) + 50)
                snippet = page_text[context_start:context_end]
                
                # Add ellipsis if truncated
                if context_start > 0:
                    snippet = "..." + snippet
                if context_end < len(page_text):
                    snippet = snippet + "..."
                
                matches.append({
                    "position": pos,
                    "snippet": snippet
                })
                
                start = pos + 1
            
            results.append({
                "page_index": page_index,
                "match_count": match_count,
                "matches": matches[:3]  # Limit to first 3 matches per page
            })
            
            total_matches += match_count
    
    return {
        "results": results,
        "total_matches": total_matches,
        "query": q,
        "pages_with_matches": len(results)
    }

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
    # Get current engine mode from settings
    try:
        with open(settings_file, "r") as f:
            settings = json.load(f)
        current_engine_mode = settings.get("engine_mode", "gpu")
    except Exception:
        current_engine_mode = "gpu"
    
    # Check which models are available
    models_dir = base_dir / "models"
    available_models = {
        "gpu": (models_dir / "kokoro.onnx").exists(),
        "cpu": (models_dir / "kokoro.int8.onnx").exists(),
        "voices": (models_dir / "voices.bin").exists()
    }
    
    return {
        "model_loaded": kokoro is not None,
        "is_loading": system_status["is_loading"],
        "is_downloading": system_status["is_downloading"],
        "last_error": system_status["last_error"],
        "voices": kokoro.get_voices() if kokoro else [],
        "engine_mode": current_engine_mode,
        "available_models": available_models
    }

@app.post("/api/system/setup")
async def run_setup(background_tasks: BackgroundTasks, model_type: Optional[str] = None):
    """
    Download and setup TTS models.
    Args:
        model_type: "gpu", "cpu", or None (uses current engine_mode setting)
    """
    if system_status["is_downloading"]: 
        return {"status": "already_running"}
    
    def setup_task():
        system_status["is_downloading"] = True
        system_status["last_error"] = None  # Clear previous errors
        try:
            # Determine which model to download
            target_model = model_type
            if target_model is None:
                try:
                    with open(settings_file, "r") as f:
                        settings = json.load(f)
                    target_model = settings.get("engine_mode", "gpu")
                except Exception:
                    target_model = "gpu"
            
            # Validate model type
            if target_model not in ["gpu", "cpu"]:
                target_model = "gpu"
            
            model_name = "Standard (GPU)" if target_model == "gpu" else "Quantized (CPU)"
            print(f"\n[SETUP] Starting download for {model_name} model...")
            print(f"[SETUP] Model type: {target_model}")
            download_kokoro_model(target_model)
            print(f"[SETUP] Download complete, loading engine...")
            load_engine(target_model)
            
            print(f"[SETUP] Setup complete!\n")
        except Exception as e: 
            error_msg = f"Setup failed: {str(e)}"
            system_status["last_error"] = error_msg
            print(f"\n[SETUP ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
        finally: 
            system_status["is_downloading"] = False
    
    background_tasks.add_task(setup_task)
    return {"status": "started"}

@app.post("/api/system/switch-engine")
async def switch_engine(background_tasks: BackgroundTasks, target_mode: str):
    """
    Switch between GPU and CPU engines.
    IMPORTANT: This endpoint only switches if the model already exists.
    It will NEVER trigger a download. Use /api/system/setup for downloads.
    
    Args:
        target_mode: "gpu" or "cpu"
    """
    if target_mode not in ["gpu", "cpu"]:
        raise HTTPException(status_code=400, detail="Invalid engine mode. Use 'gpu' or 'cpu'.")
    
    # Check if currently downloading
    if system_status["is_downloading"]:
        return {
            "status": "busy",
            "message": "Cannot switch while downloading. Please wait for download to complete."
        }
    
    # Check if target model exists
    models_dir = base_dir / "models"
    target_model_path = models_dir / ("kokoro.onnx" if target_mode == "gpu" else "kokoro.int8.onnx")
    
    if not target_model_path.exists():
        print(f"[SWITCH] {target_mode.upper()} model not found at {target_model_path}")
        return {
            "status": "model_missing",
            "message": f"{target_mode.upper()} model not downloaded. Please download it first.",
            "requires_download": True
        }
    
    # Update settings
    try:
        with open(settings_file, "r") as f:
            settings = json.load(f)
        settings["engine_mode"] = target_mode
        safe_save_json(settings_file, settings)
        print(f"[SWITCH] Updated engine_mode to {target_mode} in settings")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
    
    # Reload engine in background (non-blocking)
    def reload_task():
        if system_status["is_loading"]:
            print(f"[SWITCH] Already loading, skipping reload")
            return
        
        system_status["is_loading"] = True
        try:
            print(f"[SWITCH] Reloading engine with {target_mode} model...")
            load_engine(target_mode)
        except Exception as e:
            error_msg = f"Switch failed: {str(e)}"
            system_status["last_error"] = error_msg
            print(f"[SWITCH ERROR] {error_msg}")
        finally:
            system_status["is_loading"] = False
    
    background_tasks.add_task(reload_task)
    
    return {
        "status": "switching",
        "target_mode": target_mode,
        "message": f"Switching to {target_mode.upper()} engine..."
    }

@app.post("/api/system/download-model")
async def download_specific_model(background_tasks: BackgroundTasks, model_type: str):
    """
    Download a specific model without switching to it.
    Args:
        model_type: "gpu" or "cpu"
    """
    if model_type not in ["gpu", "cpu"]:
        raise HTTPException(status_code=400, detail="Invalid model type. Use 'gpu' or 'cpu'.")
    
    if system_status["is_downloading"]:
        return {"status": "already_downloading"}
    
    # Check if model already exists
    models_dir = base_dir / "models"
    model_path = models_dir / ("kokoro.onnx" if model_type == "gpu" else "kokoro.int8.onnx")
    
    if model_path.exists():
        return {
            "status": "already_exists",
            "message": f"{model_type.upper()} model already downloaded."
        }
    
    def download_task():
        system_status["is_downloading"] = True
        try:
            print(f"[DOWNLOAD] Fetching {model_type.upper()} model...")
            download_kokoro_model(model_type)
        except Exception as e:
            system_status["last_error"] = f"Download failed: {str(e)}"
            print(f"[DOWNLOAD ERROR] {e}")
        finally:
            system_status["is_downloading"] = False
    
    background_tasks.add_task(download_task)
    
    return {
        "status": "started",
        "model_type": model_type,
        "message": f"Downloading {model_type.upper()} model..."
    }

@app.post("/api/system/clear-cache")
async def clear_all_cache():
    """
    Clear ALL cached audio from SQLite database.
    Used by the "Clear Audio Cache" button in Voice Settings.
    Returns the number of entries deleted and space freed.
    """
    try:
        print(f"[CACHE] Clearing all cached audio...")
        
        # Clear all entries from SQLite cache
        files_deleted, freed_mb = audio_cache.clear_all()
        
        print(f"  Final: {files_deleted} entries deleted, {freed_mb:.2f} MB freed")
        print(f"[CACHE] Clear complete")
        
        return {
            "status": "success",
            "files_deleted": files_deleted,
            "freed_mb": round(freed_mb, 2),
            "message": f"Cleared {files_deleted} cache entries, freed {freed_mb:.1f} MB"
        }
    except Exception as e:
        print(f"[CACHE ERROR] Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

class SynthesisRequest(BaseModel):
    text: str
    voice: str = "af_sky"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []
    pause_settings: Optional[Dict[str, int]] = {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 800
    }

def get_language_from_voice(voice: str) -> str:
    """
    Detect language from voice ID prefix.
    Returns appropriate language code for Kokoro TTS.
    
    Voice prefix mappings:
    - af_, am_ = American English (en-us)
    - bf_, bm_ = British English (en-gb)
    - ff_, fm_ = French (fr-fr)
    - ef_, em_ = Spanish (es)
    - zf_, zm_ = Chinese (cmn)
    - if_, im_ = Italian (it)
    - pf_, pm_ = Portuguese (pt-br)
    """
    if voice.startswith(('af_', 'am_')):
        return 'en-us'
    elif voice.startswith(('bf_', 'bm_')):
        return 'en-gb'
    elif voice.startswith(('ff_', 'fm_')):
        return 'fr-fr'
    elif voice.startswith(('ef_', 'em_')):
        return 'es'
    elif voice.startswith(('zf_', 'zm_')):
        return 'cmn'  # Chinese (Mandarin)
    elif voice.startswith(('if_', 'im_')):
        return 'it'   # Italian
    elif voice.startswith(('pf_', 'pm_')):
        return 'pt-br' # Portuguese (Brazil)
    else:
        return 'en-us'  # Default fallback

def synthesize_with_pauses(text: str, voice: str, speed: float, pause_settings: Dict[str, int]) -> tuple:
    """
    Synthesize text with custom pauses using audio stitching.
    v2.3 Logic:
    - Handles punctuation groups (e.g., "...", "?!") as single pause events (based on last char).
    - Smart newline handling: Only pauses on newline if NOT preceded by punctuation.
    - v2.5 Logic: Added support for Chinese/Japanese punctuation (。，！？：；、)
    
    Returns: (audio_samples, sample_rate)
    """
    lang = get_language_from_voice(voice)
    print(f"\n{'='*60}")
    print(f"[PAUSE LOGIC v2.5] Processing: '{text[:100]}{'...' if len(text) > 100 else ''}'")
    
    # Pattern: Match text OR punctuation sequences (ASCII + CJK) OR newlines
    # Added: 。，！？：；、 (Fullwidth/Chinese punctuation)
    segments = re.split(r'([,\.!\?:;。，！？：；、]+|\n)', text)
    
    audio_segments = []
    sample_rate = SAMPLE_RATE
    
    print(f"\n[SPLIT] Text split into {len(segments)} segments")
    print(f"[SETTINGS] Pauses: {pause_settings}")
    print(f"\n[PROCESSING]")
    
    pause_count = 0
    skipped_newline_count = 0
    last_was_punctuation = False  # Track if previous valid segment was punctuation
    
    for i, segment in enumerate(segments):
        # IMPORTANT: Do NOT strip newlines here, or we lose them!
        clean_segment = segment.strip()
        
        # 1. Handle Newlines
        if segment == '\n':
            if last_was_punctuation:
                # If we just had a punctuation pause, skip the newline pause (avoid stacking)
                print(f"  [{i}] SKIP: Newline (already paused for punctuation)")
                skipped_newline_count += 1
            else:
                # Standalone newline (e.g. title or header) -> Apply "soft" pause
                # Use user setting or fallback to 300ms (to prevent "rushing")
                pause_ms = pause_settings.get('newline', 300)
                if pause_ms == 0: pause_ms = 300 # Enforce minimum breathing room
                
                pause_samples = int((pause_ms / 1000.0) * sample_rate)
                silence = np.zeros(pause_samples, dtype=np.float32)
                audio_segments.append(silence)
                pause_count += 1
                print(f"  [{i}] PAUSE: Newline = {pause_ms}ms")
            
            # Newline resets state (it's a separator, but subsequent newlines should also pause if multiple)
            # Actually, treating multiple newlines as one pause might be better, but let's stick to simple logic first.
            last_was_punctuation = False 
            continue

        # Skip empty strings (artifacts of re.split)
        if not clean_segment:
            continue

        # 2. Handle Punctuation (Single or Grouped)
        if re.match(r'^[,\.!\?:;。，！？：；、]+$', clean_segment):
            # Take the LAST character to determine pause type
            last_char = clean_segment[-1]
            
            pause_ms = 0
            if last_char in [',', '，', '、']:
                pause_ms = pause_settings.get('comma', 300)
            elif last_char in ['.', '。']:
                pause_ms = pause_settings.get('period', 600)
            elif last_char in ['?', '？']:
                pause_ms = pause_settings.get('question', 600)
            elif last_char in ['!', '！']:
                pause_ms = pause_settings.get('exclamation', 600)
            elif last_char in [':', '：']:
                pause_ms = pause_settings.get('colon', 400)
            elif last_char in [';', '；']:
                pause_ms = pause_settings.get('semicolon', 400)
            
            # Generate silent audio
            pause_samples = int((pause_ms / 1000.0) * sample_rate)
            silence = np.zeros(pause_samples, dtype=np.float32)
            audio_segments.append(silence)
            pause_count += 1
            last_was_punctuation = True
            print(f"  [{i}] PAUSE: '{clean_segment}' (as '{last_char}') = {pause_ms}ms")
        
        # 3. Handle Text
        else:
            # Re-add CJK ranges to regex to ensure we don't skip valid text
            if re.search(r'[a-zA-Z0-9\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]', clean_segment):
                try:
                    samples, _ = kokoro.create(clean_segment, voice=voice, speed=speed, lang=lang)
                    audio_segments.append(samples.flatten())
                    word_count = len(clean_segment.split())
                    print(f"  [{i}] AUDIO: '{clean_segment[:40]}{'...' if len(clean_segment) > 40 else ''}' ({word_count} words)")
                    last_was_punctuation = False
                except Exception as e:
                    print(f"  [{i}] ERROR: Synthesis failed for '{clean_segment[:30]}...': {e}")

    # Concatenate all audio segments
    if audio_segments:
        final_audio = np.concatenate(audio_segments)
        print(f"\n[COMPLETE]")
        print(f"  Pauses applied: {pause_count}")
        print(f"  Newlines skipped: {skipped_newline_count}")
        print(f"  Audio length: {len(final_audio)/sample_rate:.2f}s")
        print(f"{'='*60}\n")
        return final_audio, sample_rate
    else:
        # Return tiny silence if no audio was generated
        print(f"\n[WARNING] No audio generated - returning silence")
        print(f"{'='*60}\n")
        return np.zeros(int(sample_rate * 0.1), dtype=np.float32), sample_rate

def generate_cache_key(text: str, voice: str, speed: float, pause_settings: Dict[str, int], rules: List, ignore_list: List) -> str:
    """
    Generate MD5 hash for caching based on all synthesis parameters.
    If ANY parameter changes, the hash MUST change to force re-generation.
    """
    # Detect language from voice to include in cache key (v2.0 multilingual fix)
    lang = get_language_from_voice(voice)
    
    # Create a deterministic string from all parameters
    cache_data = {
        "text": text,
        "voice": voice,
        "language": lang,  # Include language in cache key
        "speed": speed,
        "pause_settings": pause_settings,
        "rules": [str(r) for r in rules],  # Convert to strings for hashing
        "ignore_list": sorted(ignore_list)  # Sort for consistency
    }
    
    # Convert to JSON string (sorted keys for consistency)
    cache_string = json.dumps(cache_data, sort_keys=True)
    
    # Generate MD5 hash
    hash_object = hashlib.md5(cache_string.encode('utf-8'))
    cache_hash = hash_object.hexdigest()
    
    return cache_hash

@app.post("/api/synthesize")
async def synthesize(request: SynthesisRequest):
    if kokoro is None: raise HTTPException(status_code=503, detail="TTS Engine not initialized.")
    try:
        # First, remove any [DIM] markers for TTS (don't read headers/footers)
        text = filter_text_for_tts(request.text)
        
        # Then apply pronunciation rules
        rules_data = [r.model_dump() for r in request.rules]
        text = apply_custom_pronunciations(text, rules_data, request.ignore_list)
    except Exception: 
        text = filter_text_for_tts(request.text)
    
    try:
        voices = kokoro.get_voices()
        selected_voice = request.voice if request.voice in voices else "af_sky"
        pause_settings = request.pause_settings or {}
        
        # Generate cache key
        cache_key = generate_cache_key(
            text, 
            selected_voice, 
            float(request.speed or 1.0), 
            pause_settings,
            request.rules,
            request.ignore_list
        )
        
        # Check SQLite cache first
        cached_audio = audio_cache.get(cache_key)
        if cached_audio:
            print(f"[CACHE HIT] Serving cached audio for hash {cache_key[:8]}...")
            # Return audio from memory
            return StreamingResponse(
                io.BytesIO(cached_audio),
                media_type="audio/wav",
                headers={"Content-Length": str(len(cached_audio))}
            )
        
        print(f"[CACHE MISS] Generating audio for hash {cache_key[:8]}...")
        
        # Check if custom pause settings are provided (including 0ms pauses)
        # Define these BEFORE any conditional blocks to avoid scope issues
        has_pause_settings = pause_settings and isinstance(pause_settings, dict)
        
        # Check for ASCII and CJK punctuation
        punctuation_chars = [',', '.', '!', '?', ':', ';', '\n', '。', '，', '！', '？', '：', '；', '、']
        has_punctuation = any(p in text for p in punctuation_chars)
        
        # Determine language early
        lang = get_language_from_voice(selected_voice)
        
        # Heuristic: If text has no alphanumeric or CJK characters, return tiny silence
        if not re.search(r'[a-zA-Z0-9\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]', text):
            # 0.1s silence
            samples = np.zeros(int(24000 * 0.1), dtype=np.float32)
            sample_rate = 24000
        else:
            # Normal text synthesis
            print(f"\n[PAUSE LOGIC CHECK]")
            print(f"  Has pause settings dict: {has_pause_settings}")
            print(f"  Pause settings: {pause_settings}")
            print(f"  Text has punctuation: {has_punctuation}")
            print(f"  Text preview: '{text[:100]}...'")
            print(f"  Language: {lang}")
            
            if has_pause_settings and has_punctuation:
                # Use audio stitching with custom pauses (even if some are 0ms)
                print(f"  [MODE] Using audio stitching with custom pauses")
                samples, sample_rate = synthesize_with_pauses(text, selected_voice, float(request.speed or 1.0), pause_settings)
            else:
                # Use standard synthesis (faster for simple text)
                print(f"  [MODE] Using standard synthesis (no punctuation or no pause settings)")
                samples, sample_rate = kokoro.create(text, voice=selected_voice, speed=float(request.speed or 1.0), lang=lang)
        
        # Convert audio to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, samples.flatten(), sample_rate, format='WAV', subtype='PCM_16')
        audio_bytes = buffer.getvalue()
        
        # Save to SQLite cache (LRU cleanup handled automatically)
        audio_cache.put(cache_key, audio_bytes)
        print(f"[CACHE SAVE] Audio saved to DB: {cache_key[:8]}... ({len(audio_bytes)} bytes)")
        
        # Stream the audio
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={"Content-Length": str(len(audio_bytes))}
        )
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# MP3 Export API
class ExportRequest(BaseModel):
    doc_id: str
    voice: str = "af_bella"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []

@app.get("/api/ffmpeg/status")
async def get_ffmpeg_status():
    return ffmpeg_status

@app.post("/api/ffmpeg/install")
async def install_ffmpeg(background_tasks: BackgroundTasks):
    global ffmpeg_status, ffmpeg_installer
    
    if ffmpeg_status["is_downloading"]:
        return JSONResponse({"error": "Download already in progress"}, status_code=409)
    
    if ffmpeg_status["is_installed"]:
        return {"status": "already_installed"}
    
    def download_task():
        global ffmpeg_status, ffmpeg_installer
        ffmpeg_status["is_downloading"] = True
        ffmpeg_status["progress"] = 0
        ffmpeg_status["total"] = 0
        ffmpeg_status["error"] = None
        ffmpeg_status["message"] = "Starting download..."
        
        def progress_callback(current, total, message):
            ffmpeg_status["progress"] = current
            ffmpeg_status["total"] = total
            ffmpeg_status["message"] = message
        
        ffmpeg_installer = FFMPEGInstaller(progress_callback)
        success, error = ffmpeg_installer.install()
        
        if success:
            ffmpeg_status["is_installed"] = True
            ffmpeg_status["is_downloading"] = False
            ffmpeg_status["message"] = "Installation complete"
            # Configure pydub to use local FFMPEG
            try:
                configure_pydub()
            except Exception as e:
                print(f"Warning: Failed to configure pydub: {e}")
        else:
            ffmpeg_status["error"] = error
            ffmpeg_status["is_downloading"] = False
        
        ffmpeg_installer = None
    
    background_tasks.add_task(download_task)
    return {"status": "started"}

@app.post("/api/ffmpeg/cancel")
async def cancel_ffmpeg_download():
    global ffmpeg_installer
    if ffmpeg_installer:
        ffmpeg_installer.cancel()
        return {"status": "cancelled"}
    return {"status": "not_running"}

@app.post("/api/export/audio")
async def export_audio(request: ExportRequest, background_tasks: BackgroundTasks):
    global export_status, ffmpeg_status
    if export_status["is_exporting"]:
        return JSONResponse({"error": "Export already in progress"}, status_code=409)
    
    if kokoro is None:
        raise HTTPException(status_code=503, detail="TTS Engine not initialized.")
    
    # Check if FFMPEG is installed
    if not ffmpeg_status["is_installed"]:
        raise HTTPException(status_code=503, detail="FFMPEG not installed. Please install it first.")
    
    # Configure pydub before export
    try:
        configure_pydub()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure audio encoder: {str(e)}")
    
    def export_task():
        global export_status
        export_status = {"is_exporting": True, "progress": 0, "total": 0, "error": None, "output_file": None}
        
        try:
            # 1. Load document content
            content_file = content_dir / f"{request.doc_id}.json"
            if not content_file.exists():
                export_status["error"] = "Document not found"
                return
            
            with open(content_file, "r") as f:
                doc_data = json.load(f)
            
            # 2. Load library item for filename
            with open(library_file, "r") as f:
                library = json.load(f)
            
            doc_item = next((item for item in library if item.get("id") == request.doc_id), None)
            if not doc_item:
                export_status["error"] = "Document metadata not found"
                return
            
            # 3. Split text into manageable chunks (avoid MAX_PHONEME_LENGTH truncation)
            # Split by sentences/paragraphs to ensure each chunk is processable
            chunks = []
            
            for page in doc_data.get("pages", []):
                # Split page by newlines (paragraphs)
                page_paragraphs = [p.strip() for p in page.split('\n') if p.strip()]
                
                for para in page_paragraphs:
                    # If paragraph is still too long (>500 chars), split by sentences
                    if len(para) > 500:
                        # Split by sentence-ending punctuation
                        sentences = re.split(r'(?<=[.!?])\s+', para)
                        chunks.extend([s.strip() for s in sentences if s.strip()])
                    else:
                        chunks.append(para)
            
            export_status["total"] = len(chunks)
            
            # 4. Process each chunk
            audio_segments = []
            rules_data = [r.model_dump() for r in request.rules]
            
            for i, chunk in enumerate(chunks):
                if not export_status["is_exporting"]:  # Check for cancellation
                    export_status["error"] = "Export cancelled"
                    return
                
                try:
                    # First filter out dimmed text (headers/footers)
                    filtered_text = filter_text_for_tts(chunk)
                    
                    # Skip empty chunks
                    if not filtered_text or not re.search(r'[a-zA-Z0-9]', filtered_text):
                        export_status["progress"] = i + 1
                        continue
                    
                    # Then apply pronunciation rules
                    processed_text = apply_custom_pronunciations(filtered_text, rules_data, request.ignore_list)
                    
                    # Generate audio with language detection
                    lang = get_language_from_voice(request.voice)
                    samples, sample_rate = kokoro.create(
                        processed_text,
                        voice=request.voice,
                        speed=float(request.speed),
                        lang=lang
                    )
                    
                    # Convert to AudioSegment
                    buffer = io.BytesIO()
                    sf.write(buffer, samples.flatten(), sample_rate, format='WAV', subtype='PCM_16')
                    buffer.seek(0)
                    audio_segment = AudioSegment.from_wav(buffer)
                    audio_segments.append(audio_segment)
                    
                    # Add small pause between chunks (300ms)
                    silence = AudioSegment.silent(duration=300)
                    audio_segments.append(silence)
                    
                except Exception as e:
                    print(f"Warning: Failed to process chunk {i}: {e}")
                    # Continue with next chunk
                
                export_status["progress"] = i + 1
            
            # 5. Combine all segments
            if not audio_segments:
                export_status["error"] = "No audio generated"
                return
            
            final_audio = sum(audio_segments)
            
            # 6. Save as MP3
            safe_filename = re.sub(r'[^\w\s-]', '', doc_item.get("fileName", "export")).replace(' ', '_')
            output_filename = f"{safe_filename}_{request.voice}.mp3"
            output_path = userdata_dir / output_filename
            
            final_audio.export(str(output_path), format="mp3", bitrate="128k")
            
            export_status["output_file"] = output_filename
            export_status["is_exporting"] = False
            
        except Exception as e:
            export_status["error"] = str(e)
            export_status["is_exporting"] = False
    
    background_tasks.add_task(export_task)
    return {"status": "started"}

@app.get("/api/export/status")
async def get_export_status():
    return export_status

@app.post("/api/export/cancel")
async def cancel_export():
    global export_status
    if export_status["is_exporting"]:
        export_status["is_exporting"] = False
        return {"status": "cancelled"}
    return {"status": "not_running"}

@app.get("/api/export/download/{filename}")
async def download_export(filename: str):
    file_path = userdata_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)

@app.post("/api/export/open-location/{filename}")
async def open_file_location(filename: str):
    """
    Opens the folder containing the exported file.
    Uses absolute path anchoring to ensure reliability regardless of CWD.
    """
    try:
        # Step 1: Resolve absolute path using anchored userdata_dir
        # This is immune to where the user launched the terminal from
        file_path = userdata_dir / filename
        abs_file_path = file_path.absolute()
        
        print(f"[LOOKUP] Looking for file: {abs_file_path}")
        
        # Step 2: Verify file exists
        if not abs_file_path.exists():
            print(f"[ERROR] File not found: {abs_file_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Step 3: Get the folder path
        folder_path = abs_file_path.parent
        
        # Step 4: Verify folder exists (should always be true if file exists)
        if not folder_path.exists():
            # This should be impossible, but handle it gracefully
            print(f"[WARNING] Folder missing, creating: {folder_path}")
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # Step 5: Open folder (platform-specific, using native APIs)
        system = platform.system()
        folder_str = str(folder_path)
        
        print(f"[OPEN] Opening folder: {folder_str}")
        print(f"   Platform: {system}")
        print(f"   File: {filename}")
        
        if system == "Windows":
            # Windows native API - bulletproof
            os.startfile(folder_str)
            
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", folder_str])
            
        elif system == "Linux":
            subprocess.Popen(["xdg-open", folder_str])
            
        else:
            raise HTTPException(status_code=501, detail=f"Platform '{system}' not supported")
        
        return {
            "status": "opened",
            "folder": folder_str,
            "file": filename,
            "absolute_path": str(abs_file_path)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to open folder: {str(e)}"
        print(f"[CRITICAL] {error_msg}")
        print(f"   File requested: {filename}")
        print(f"   Userdata dir: {userdata_dir}")
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
