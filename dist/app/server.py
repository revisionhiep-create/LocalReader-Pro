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
cache_dir = get_app_anchored_path(".cache")  # Audio cache directory

# Cache Management Settings
MAX_CACHE_SIZE_MB = 100  # Maximum cache size in megabytes
MAX_FILE_AGE_DAYS = 7    # Delete files older than this many days

# Ensure dirs exist (with clear logging)
try:
    userdata_dir.mkdir(exist_ok=True)
    content_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)
    print(f"[OK] Storage initialized at: {userdata_dir}")
    print(f"[OK] Audio cache initialized at: {cache_dir}")
except Exception as e:
    print(f"[CRITICAL] Failed to create storage dirs: {e}")
    print(f"           Attempted path: {userdata_dir}")

# =============================================================================
# CACHE MANAGEMENT FUNCTIONS
# =============================================================================

def get_cache_size_mb() -> float:
    """Calculate total size of cache directory in MB."""
    total_size = 0
    try:
        for file_path in cache_dir.glob("*.wav"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except Exception as e:
        print(f"[WARNING] Failed to calculate cache size: {e}")
    return total_size / (1024 * 1024)  # Convert bytes to MB

def get_cache_file_count() -> int:
    """Count number of files in cache directory."""
    try:
        return len(list(cache_dir.glob("*.wav")))
    except Exception:
        return 0

def cleanup_old_cache_files(max_age_days: int = MAX_FILE_AGE_DAYS) -> int:
    """
    Delete cache files older than max_age_days.
    Returns number of files deleted.
    """
    deleted_count = 0
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    try:
        for file_path in cache_dir.glob("*.wav"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
    except Exception as e:
        print(f"[WARNING] Error during age-based cleanup: {e}")
    
    return deleted_count

def cleanup_cache_by_size(max_size_mb: float = MAX_CACHE_SIZE_MB) -> int:
    """
    Delete oldest cache files (LRU) until total size is under max_size_mb.
    Returns number of files deleted.
    """
    deleted_count = 0
    current_size = get_cache_size_mb()
    
    if current_size <= max_size_mb:
        return 0  # Cache is within limit
    
    try:
        # Get all cache files with their access times
        files_with_time = []
        for file_path in cache_dir.glob("*.wav"):
            if file_path.is_file():
                # Use atime (access time) for LRU, fallback to mtime
                try:
                    access_time = file_path.stat().st_atime
                except:
                    access_time = file_path.stat().st_mtime
                file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                files_with_time.append((file_path, access_time, file_size))
        
        # Sort by access time (oldest first)
        files_with_time.sort(key=lambda x: x[1])
        
        # Delete oldest files until we're under the limit
        for file_path, _, file_size in files_with_time:
            if current_size <= max_size_mb:
                break
            file_path.unlink()
            current_size -= file_size
            deleted_count += 1
            
    except Exception as e:
        print(f"[WARNING] Error during size-based cleanup: {e}")
    
    return deleted_count

def run_cache_cleanup():
    """
    Run full cache cleanup: age-based and size-based.
    Called on app startup and periodically.
    """
    print(f"\n[CACHE CLEANUP] Starting...")
    
    # Get initial stats
    initial_count = get_cache_file_count()
    initial_size = get_cache_size_mb()
    print(f"  Initial: {initial_count} files, {initial_size:.2f} MB")
    
    # Step 1: Delete old files (age-based)
    age_deleted = cleanup_old_cache_files(MAX_FILE_AGE_DAYS)
    if age_deleted > 0:
        print(f"  Deleted {age_deleted} files older than {MAX_FILE_AGE_DAYS} days")
    
    # Step 2: Check size limit (LRU-based)
    size_deleted = cleanup_cache_by_size(MAX_CACHE_SIZE_MB)
    if size_deleted > 0:
        print(f"  Deleted {size_deleted} oldest files to fit {MAX_CACHE_SIZE_MB}MB limit")
    
    # Get final stats
    final_count = get_cache_file_count()
    final_size = get_cache_size_mb()
    total_deleted = age_deleted + size_deleted
    
    if total_deleted > 0:
        print(f"  Final: {final_count} files, {final_size:.2f} MB (freed {initial_size - final_size:.2f} MB)")
    else:
        print(f"  No cleanup needed (within limits)")
    
    print(f"[CACHE CLEANUP] Complete\n")

# =============================================================================
# END CACHE MANAGEMENT
# =============================================================================

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
    "pause_settings": {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 800
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
    from logic.downloader import download_kokoro_model
    from logic.dependency_manager import FFMPEGInstaller, get_ffmpeg_path, configure_pydub
    from logic.smart_content_detector import find_content_start_page, detect_headers_footers, apply_header_footer_filter, filter_text_for_tts
except ImportError:
    sys.path.append(str(base_dir / "logic"))
    from text_normalizer import apply_custom_pronunciations, inject_pauses
    from downloader import download_kokoro_model
    from dependency_manager import FFMPEGInstaller, get_ffmpeg_path, configure_pydub
    from smart_content_detector import find_content_start_page, detect_headers_footers, apply_header_footer_filter, filter_text_for_tts

# Global engine
kokoro = None
system_status = {"is_loading": False, "last_error": None, "is_downloading": False}
export_status = {"is_exporting": False, "progress": 0, "total": 0, "error": None, "output_file": None}
ffmpeg_status = {"is_installed": False, "is_downloading": False, "progress": 0, "total": 0, "error": None, "message": ""}
ffmpeg_installer = None

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
    global ffmpeg_status
    threading.Thread(target=load_engine, daemon=True).start()
    # Check FFMPEG on startup
    installer = FFMPEGInstaller()
    ffmpeg_status["is_installed"] = installer.check_installed()
    # Run cache cleanup on startup
    run_cache_cleanup()
    yield

app = FastAPI(title="LocalReader Pro API", lifespan=lifespan)

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
    pause_settings: Optional[Dict[str, int]] = {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 800
    }

def synthesize_with_pauses(text: str, voice: str, speed: float, pause_settings: Dict[str, int]) -> tuple:
    """
    Synthesize text with custom pauses using audio stitching.
    NEW LOGIC: Only apply pauses to SINGLE punctuation marks at sentence ends.
    Ignores consecutive/mixed punctuation (e.g., "...", "?!", "!!!") entirely.
    
    Returns: (audio_samples, sample_rate)
    """
    print(f"\n{'='*60}")
    print(f"[PAUSE LOGIC] Processing: '{text[:100]}{'...' if len(text) > 100 else ''}'")
    print(f"{'='*60}")
    
    # NEW APPROACH: Split by punctuation but capture sequences (not individual chars)
    # This pattern captures groups of punctuation together: "..." stays as "...", not split into 3
    # Pattern: Match text OR punctuation sequences OR newlines
    segments = re.split(r'([,\.!\?:;]+|\n)', text)
    
    audio_segments = []
    sample_rate = SAMPLE_RATE
    
    print(f"\n[SPLIT] Text split into {len(segments)} segments")
    print(f"[SETTINGS] Pauses: {pause_settings}")
    print(f"\n[PROCESSING]")
    
    pause_count = 0
    skip_count = 0
    
    for i, segment in enumerate(segments):
        segment = segment.strip()
        if not segment:
            continue
        
        # Check if segment is punctuation
        if re.match(r'^[,\.!\?:;]+$', segment):
            # Check if it's SINGLE punctuation (apply pause) or MULTIPLE (skip)
            if len(segment) == 1:
                # Single punctuation - apply pause
                pause_ms = 0
                if segment == ',':
                    pause_ms = pause_settings.get('comma', 300)
                elif segment == '.':
                    pause_ms = pause_settings.get('period', 600)
                elif segment == '?':
                    pause_ms = pause_settings.get('question', 600)
                elif segment == '!':
                    pause_ms = pause_settings.get('exclamation', 600)
                elif segment == ':':
                    pause_ms = pause_settings.get('colon', 400)
                elif segment == ';':
                    pause_ms = pause_settings.get('semicolon', 400)
                
                # Generate silent audio
                pause_samples = int((pause_ms / 1000.0) * sample_rate)
                silence = np.zeros(pause_samples, dtype=np.float32)
                audio_segments.append(silence)
                pause_count += 1
                print(f"  [{i}] PAUSE: '{segment}' = {pause_ms}ms")
            else:
                # Multiple/mixed punctuation - SKIP pause entirely
                skip_count += 1
                print(f"  [{i}] SKIP: '{segment}' (consecutive/mixed punctuation - ignored)")
        
        elif segment == '\n':
            # Add newline pause
            pause_ms = pause_settings.get('newline', 800)
            pause_samples = int((pause_ms / 1000.0) * sample_rate)
            silence = np.zeros(pause_samples, dtype=np.float32)
            audio_segments.append(silence)
            pause_count += 1
            print(f"  [{i}] PAUSE: newline = {pause_ms}ms")
        
        else:
            # Generate audio for text segment
            if re.search(r'[a-zA-Z0-9]', segment):
                try:
                    samples, _ = kokoro.create(segment, voice=voice, speed=speed, lang="en-us")
                    audio_segments.append(samples.flatten())
                    word_count = len(segment.split())
                    print(f"  [{i}] AUDIO: '{segment[:40]}{'...' if len(segment) > 40 else ''}' ({word_count} words)")
                except Exception as e:
                    print(f"  [{i}] ERROR: Synthesis failed for '{segment[:30]}...': {e}")
    
    # Concatenate all audio segments
    if audio_segments:
        final_audio = np.concatenate(audio_segments)
        print(f"\n[COMPLETE]")
        print(f"  Pauses applied: {pause_count}")
        print(f"  Pauses skipped: {skip_count} (consecutive/mixed)")
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
    # Create a deterministic string from all parameters
    cache_data = {
        "text": text,
        "voice": voice,
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
        cache_file = cache_dir / f"{cache_key}.wav"
        
        # Check cache first
        if cache_file.exists():
            print(f"[CACHE HIT] Serving cached audio for hash {cache_key[:8]}...")
            return FileResponse(cache_file, media_type="audio/wav")
        
        print(f"[CACHE MISS] Generating audio for hash {cache_key[:8]}...")
        
        # Check if custom pause settings are provided (including 0ms pauses)
        # Define these BEFORE any conditional blocks to avoid scope issues
        has_pause_settings = pause_settings and isinstance(pause_settings, dict)
        has_punctuation = any(p in text for p in [',', '.', '!', '?', ':', ';', '\n'])
        
        # Heuristic: If text has no alphanumeric characters, return tiny silence
        if not re.search(r'[a-zA-Z0-9]', text):
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
            
            if has_pause_settings and has_punctuation:
                # Use audio stitching with custom pauses (even if some are 0ms)
                print(f"  [MODE] Using audio stitching with custom pauses")
                samples, sample_rate = synthesize_with_pauses(text, selected_voice, float(request.speed or 1.0), pause_settings)
            else:
                # Use standard synthesis (faster for simple text)
                print(f"  [MODE] Using standard synthesis (no punctuation or no pause settings)")
                samples, sample_rate = kokoro.create(text, voice=selected_voice, speed=float(request.speed or 1.0), lang="en-us")
        
        # Check cache size before saving (cleanup if needed)
        current_cache_size = get_cache_size_mb()
        if current_cache_size > MAX_CACHE_SIZE_MB * 0.9:  # Cleanup at 90% threshold
            print(f"[CACHE] Size {current_cache_size:.1f}MB approaching limit, running cleanup...")
            cleanup_cache_by_size(MAX_CACHE_SIZE_MB)
        
        # Save to cache
        sf.write(str(cache_file), samples.flatten(), sample_rate, format='WAV', subtype='PCM_16')
        print(f"[CACHE SAVE] Audio saved: {cache_file.name}")
        
        # Stream the cached file
        return FileResponse(cache_file, media_type="audio/wav")
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
            
            # 3. Combine all pages into paragraphs
            full_text = "\n\n".join(doc_data.get("pages", []))
            paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
            
            export_status["total"] = len(paragraphs)
            
            # 4. Process each paragraph
            audio_segments = []
            rules_data = [r.model_dump() for r in request.rules]
            
            for i, paragraph in enumerate(paragraphs):
                if not export_status["is_exporting"]:  # Check for cancellation
                    export_status["error"] = "Export cancelled"
                    return
                
                try:
                    # First filter out dimmed text (headers/footers)
                    filtered_paragraph = filter_text_for_tts(paragraph)
                    
                    # Then apply pronunciation rules
                    processed_text = apply_custom_pronunciations(filtered_paragraph, rules_data, request.ignore_list)
                    
                    # Generate audio
                    samples, sample_rate = kokoro.create(
                        processed_text,
                        voice=request.voice,
                        speed=float(request.speed),
                        lang="en-us"
                    )
                    
                    # Convert to AudioSegment
                    buffer = io.BytesIO()
                    sf.write(buffer, samples.flatten(), sample_rate, format='WAV', subtype='PCM_16')
                    buffer.seek(0)
                    audio_segment = AudioSegment.from_wav(buffer)
                    audio_segments.append(audio_segment)
                    
                    # Add small pause between paragraphs (500ms)
                    silence = AudioSegment.silent(duration=500)
                    audio_segments.append(silence)
                    
                except Exception as e:
                    print(f"Warning: Failed to process paragraph {i}: {e}")
                    # Continue with next paragraph
                
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
