from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from ..state import export_status, ffmpeg_status, kokoro
from ..config import content_dir, library_file, userdata_dir
from ..models import ExportRequest
from ..utils import get_language_from_voice
import json
import re
import io
import os
import platform
import subprocess
import soundfile as sf
from pydub import AudioSegment
import sys
from pathlib import Path

# Fix paths for logic imports
base_dir_parent = Path(__file__).parent.parent
if str(base_dir_parent) not in sys.path:
    sys.path.append(str(base_dir_parent))

try:
    from logic.dependency_manager import FFMPEGInstaller, configure_pydub
    from logic.smart_content_detector import filter_text_for_tts
    from logic.text_normalizer import apply_custom_pronunciations
except ImportError:
    sys.path.append(str(base_dir_parent / "logic"))
    from dependency_manager import FFMPEGInstaller, configure_pydub
    from smart_content_detector import filter_text_for_tts
    from text_normalizer import apply_custom_pronunciations

router = APIRouter()
ffmpeg_installer = None


@router.get("/api/ffmpeg/status")
async def get_ffmpeg_status():
    return ffmpeg_status


@router.post("/api/ffmpeg/install")
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


@router.post("/api/ffmpeg/cancel")
async def cancel_ffmpeg_download():
    global ffmpeg_installer
    if ffmpeg_installer:
        ffmpeg_installer.cancel()
        return {"status": "cancelled"}
    return {"status": "not_running"}


@router.post("/api/export/audio")
async def export_audio(request: ExportRequest, background_tasks: BackgroundTasks):
    global export_status
    if export_status["is_exporting"]:
        return JSONResponse({"error": "Export already in progress"}, status_code=409)

    # Access kokoro from state module
    import app.state as state_module

    if state_module.kokoro is None:
        raise HTTPException(status_code=503, detail="TTS Engine not initialized.")

    if not ffmpeg_status["is_installed"]:
        # Re-check in case it was installed externally
        installer = FFMPEGInstaller()
        if not installer.check_installed():
            raise HTTPException(
                status_code=503, detail="FFMPEG not installed. Please install it first."
            )
        else:
            ffmpeg_status["is_installed"] = True

    try:
        configure_pydub()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to configure audio encoder: {str(e)}"
        )

    def export_task():
        global export_status
        export_status = {
            "is_exporting": True,
            "progress": 0,
            "total": 0,
            "error": None,
            "output_file": None,
        }

        try:
            content_file = content_dir / f"{request.doc_id}.json"
            if not content_file.exists():
                export_status["error"] = "Document not found"
                export_status["is_exporting"] = False
                return

            with open(content_file, "r") as f:
                doc_data = json.load(f)

            with open(library_file, "r") as f:
                library = json.load(f)

            doc_item = next(
                (item for item in library if item.get("id") == request.doc_id), None
            )
            if not doc_item:
                export_status["error"] = "Document metadata not found"
                export_status["is_exporting"] = False
                return

            chunks = []
            for page in doc_data.get("pages", []):
                page_paragraphs = [p.strip() for p in page.split("\n") if p.strip()]
                for para in page_paragraphs:
                    if len(para) > 500:
                        sentences = re.split(r"(?<=[.!?])\s+", para)
                        chunks.extend([s.strip() for s in sentences if s.strip()])
                    else:
                        chunks.append(para)

            export_status["total"] = len(chunks)
            audio_segments = []
            rules_data = [r.model_dump() for r in request.rules]

            for i, chunk in enumerate(chunks):
                if not export_status["is_exporting"]:
                    export_status["error"] = "Export cancelled"
                    return

                try:
                    filtered_text = filter_text_for_tts(chunk)
                    if not filtered_text or not re.search(
                        r"[a-zA-Z0-9]", filtered_text
                    ):
                        export_status["progress"] = i + 1
                        continue

                    processed_text = apply_custom_pronunciations(
                        filtered_text, rules_data, request.ignore_list
                    )

                    lang = get_language_from_voice(request.voice)

                    # Use state_module.kokoro
                    samples, sample_rate = state_module.kokoro.create(
                        processed_text,
                        voice=request.voice,
                        speed=float(request.speed),
                        lang=lang,
                    )

                    buffer = io.BytesIO()
                    sf.write(
                        buffer,
                        samples.flatten(),
                        sample_rate,
                        format="WAV",
                        subtype="PCM_16",
                    )
                    buffer.seek(0)
                    audio_segment = AudioSegment.from_wav(buffer)
                    audio_segments.append(audio_segment)
                    audio_segments.append(AudioSegment.silent(duration=300))

                except Exception as e:
                    print(f"Warning: Failed to process chunk {i}: {e}")

                export_status["progress"] = i + 1

            if not audio_segments:
                export_status["error"] = "No audio generated"
                export_status["is_exporting"] = False
                return

            final_audio = sum(audio_segments)
            safe_filename = re.sub(
                r"[^\w\s-]", "", doc_item.get("fileName", "export")
            ).replace(" ", "_")
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


@router.get("/api/export/status")
async def get_export_status():
    return export_status


@router.post("/api/export/cancel")
async def cancel_export():
    global export_status
    if export_status["is_exporting"]:
        export_status["is_exporting"] = False
        return {"status": "cancelled"}
    return {"status": "not_running"}


@router.get("/api/export/download/{filename}")
async def download_export(filename: str):
    file_path = userdata_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


@router.post("/api/export/open-location/{filename}")
async def open_file_location(filename: str):
    try:
        file_path = userdata_dir / filename
        abs_file_path = file_path.absolute()

        if not abs_file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        folder_path = abs_file_path.parent
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)

        system = platform.system()
        folder_str = str(folder_path)

        if system == "Windows":
            os.startfile(folder_str)
        elif system == "Darwin":
            subprocess.Popen(["open", folder_str])
        elif system == "Linux":
            subprocess.Popen(["xdg-open", folder_str])
        else:
            raise HTTPException(status_code=501, detail="Platform not supported")

        return {"status": "opened", "folder": folder_str}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
