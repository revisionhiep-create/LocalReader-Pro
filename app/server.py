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

# Ensure dirs exist (with clear logging)
try:
    userdata_dir.mkdir(exist_ok=True)
    content_dir.mkdir(exist_ok=True)
    print(f"✅ Storage initialized at: {userdata_dir}")
except Exception as e:
    print(f"❌ CRITICAL: Failed to create storage dirs: {e}")
    print(f"   Attempted path: {userdata_dir}")

def safe_init_json(path: Path, default_data: Any):
    if not path.exists():
        with open(path, "w") as f:
            json.dump(default_data, f)

safe_init_json(settings_file, {
    "pronunciationRules": [], 
    "ignoreList": [],
    "voice_id": "af_bella",
    "speed": 1.0,
    "header_footer_mode": "off"  # Options: "off", "clean", "dim"
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

# Import logic
try:
    from logic.text_normalizer import apply_custom_pronunciations
    from logic.downloader import download_kokoro_model
    from logic.dependency_manager import FFMPEGInstaller, get_ffmpeg_path, configure_pydub
    from logic.smart_content_detector import find_content_start_page, detect_headers_footers, apply_header_footer_filter, filter_text_for_tts
    from logic.dialogue_flow_manager import DialogueFlowManager
except ImportError:
    sys.path.append(str(base_dir / "logic"))
    from text_normalizer import apply_custom_pronunciations
    from downloader import download_kokoro_model
    from dependency_manager import FFMPEGInstaller, get_ffmpeg_path, configure_pydub
    from smart_content_detector import find_content_start_page, detect_headers_footers, apply_header_footer_filter, filter_text_for_tts
    from dialogue_flow_manager import DialogueFlowManager

# Global engine
kokoro = None
dialogue_manager = DialogueFlowManager(use_ssml=False)  # Initialize dialogue flow manager
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
    yield

app = FastAPI(title="LocalReader Pro v1.5 API", lifespan=lifespan)

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

class SynthesisWithContextRequest(BaseModel):
    text: str
    context_before: List[str] = []  # Up to 2 sentences before
    context_after: List[str] = []   # Up to 2 sentences after
    voice: str = "af_sky"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []

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

@app.post("/api/synthesize/with-context")
async def synthesize_with_context(request: SynthesisWithContextRequest):
    """
    Enhanced synthesis endpoint with context-aware pause calculation.
    Uses DialogueFlowManager to determine natural pause duration.
    """
    if kokoro is None:
        raise HTTPException(status_code=503, detail="TTS Engine not initialized.")
    
    try:
        # Process text (remove [DIM] markers and apply pronunciation rules)
        text = filter_text_for_tts(request.text)
        rules_data = [r.model_dump() for r in request.rules]
        processed_text = apply_custom_pronunciations(text, rules_data, request.ignore_list)
    except Exception as e:
        print(f"Warning: Text processing failed: {e}")
        processed_text = filter_text_for_tts(request.text)
    
    # Build context for classification (use original text to preserve quotes/formatting)
    context_paragraphs = []
    context_paragraphs.extend(request.context_before)
    context_paragraphs.append(request.text)  # Original text needed for accurate dialogue detection
    context_paragraphs.extend(request.context_after)
    
    # Use DialogueFlowManager to classify and calculate pause
    context_text = "\n\n".join(context_paragraphs)
    segments = dialogue_manager.process_chapter(context_text)
    
    # Find the current sentence segment (should be at index len(context_before))
    target_index = len(request.context_before)
    pause_after = 0.5  # Default fallback
    
    if target_index < len(segments):
        pause_after = segments[target_index]["pause_after"]
    
    # Generate audio
    try:
        voices = kokoro.get_voices()
        selected_voice = request.voice if request.voice in voices else "af_sky"
        
        # Heuristic: If text has no alphanumeric characters, return tiny silence
        if not re.search(r'[a-zA-Z0-9]', processed_text):
            samples = np.zeros(int(24000 * 0.1), dtype=np.float32)
            sample_rate = 24000
        else:
            samples, sample_rate = kokoro.create(
                processed_text,
                voice=selected_voice,
                speed=float(request.speed or 1.0),
                lang="en-us"
            )
        
        # Encode audio
        buffer = io.BytesIO()
        sf.write(buffer, samples.flatten(), sample_rate, format='WAV', subtype='PCM_16')
        buffer.seek(0)
        
        # Return audio stream with pause metadata in custom header
        return StreamingResponse(
            buffer, 
            media_type="audio/wav",
            headers={
                "X-Pause-After": str(pause_after),  # Custom header for pause duration
                "X-Sample-Rate": str(sample_rate)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            
            # 3. Combine all pages and process with DialogueFlowManager
            full_text = "\n\n".join(doc_data.get("pages", []))
            
            # Use DialogueFlowManager to intelligently split text
            segments = dialogue_manager.process_chapter(full_text)
            
            export_status["total"] = len(segments)
            
            # 4. Process each segment with smart pausing
            audio_segments = []
            rules_data = [r.model_dump() for r in request.rules]
            
            for i, segment in enumerate(segments):
                if not export_status["is_exporting"]:  # Check for cancellation
                    export_status["error"] = "Export cancelled"
                    return
                
                try:
                    # Get text from segment
                    text = segment["text"]
                    pause_duration = segment["pause_after"]
                    
                    # First filter out dimmed text (headers/footers)
                    filtered_text = filter_text_for_tts(text)
                    
                    # Skip empty segments
                    if not filtered_text.strip():
                        export_status["progress"] = i + 1
                        continue
                    
                    # Then apply pronunciation rules
                    processed_text = apply_custom_pronunciations(filtered_text, rules_data, request.ignore_list)
                    
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
                    
                    # Add smart pause based on segment type (DialogueFlowManager logic)
                    # Convert seconds to milliseconds
                    pause_ms = int(pause_duration * 1000)
                    if pause_ms > 0:
                        silence = AudioSegment.silent(duration=pause_ms)
                        audio_segments.append(silence)
                    
                except Exception as e:
                    print(f"Warning: Failed to process segment {i}: {e}")
                    # Continue with next segment
                
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
        
        print(f"🔍 Looking for file: {abs_file_path}")
        
        # Step 2: Verify file exists
        if not abs_file_path.exists():
            print(f"❌ File not found: {abs_file_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Step 3: Get the folder path
        folder_path = abs_file_path.parent
        
        # Step 4: Verify folder exists (should always be true if file exists)
        if not folder_path.exists():
            # This should be impossible, but handle it gracefully
            print(f"⚠️ Folder missing, creating: {folder_path}")
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # Step 5: Open folder (platform-specific, using native APIs)
        system = platform.system()
        folder_str = str(folder_path)
        
        print(f"✅ Opening folder: {folder_str}")
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
        print(f"❌ CRITICAL ERROR: {error_msg}")
        print(f"   File requested: {filename}")
        print(f"   Userdata dir: {userdata_dir}")
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
