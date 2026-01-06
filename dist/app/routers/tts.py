from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import numpy as np
import io
import re
import hashlib
import soundfile as sf
import concurrent.futures
from typing import Dict
import sys
import json
from pathlib import Path

# Add app logic to path for imports
base_dir_parent = Path(__file__).parent.parent
if str(base_dir_parent) not in sys.path:
    sys.path.append(str(base_dir_parent))

try:
    from logic.smart_content_detector import filter_text_for_tts
    from logic.text_normalizer import apply_custom_pronunciations
except ImportError:
    sys.path.append(str(base_dir_parent / "logic"))
    from smart_content_detector import filter_text_for_tts
    from text_normalizer import apply_custom_pronunciations

from ..state import audio_cache, kokoro
from ..models import SynthesisRequest
from ..utils import get_language_from_voice
from ..config import base_dir
from kokoro_onnx import SAMPLE_RATE

router = APIRouter()

# --- Helpers moved from server.py ---


def safe_concat(audio_list):
    clean_list = []
    for a in audio_list:
        if isinstance(a, np.ndarray):
            if a.ndim == 2:
                a = a.squeeze()
            if a.ndim > 2:
                a = a.flatten()
        clean_list.append(a)
    if not clean_list:
        return np.array([], dtype=np.float32)
    return np.concatenate(clean_list)


def synthesize_with_pauses(
    text: str, voice: str, speed: float, pause_settings: Dict[str, int]
):
    import app.state as state_module

    lang = get_language_from_voice(voice)
    segments = re.split(r"([,\.!\?:;。，！？：；、]+|\n)", text)
    sample_rate = SAMPLE_RATE
    plan = []
    last_was_punctuation = False

    char_map = {
        ",": "comma",
        "，": "comma",
        "、": "comma",
        ".": "period",
        "。": "period",
        "?": "question",
        "？": "question",
        "!": "exclamation",
        "！": "exclamation",
        ":": "colon",
        "：": "colon",
        ";": "semicolon",
        "；": "semicolon",
    }

    for i, segment in enumerate(segments):
        clean_segment = segment.strip()
        if segment == "\n":
            if not last_was_punctuation:
                ms = pause_settings.get("newline", 300) or 300
                plan.append({"type": "silence", "ms": ms})
            last_was_punctuation = False
            continue

        if not clean_segment:
            continue

        if re.match(r"^[,\.!\?:;。，！？：；、]+$", clean_segment):
            last_char = clean_segment[-1]
            pause_ms = 0

            vocab_key = char_map.get(last_char)
            if vocab_key:
                pause_ms = pause_settings.get(vocab_key, 300)

            plan.append({"type": "silence", "ms": pause_ms})
            last_was_punctuation = True
        else:
            if re.search(
                r"[a-zA-Z0-9\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]",
                clean_segment,
            ):
                plan.append({"type": "tts", "text": clean_segment, "index": i})
                last_was_punctuation = False

    tts_tasks = [p for p in plan if p["type"] == "tts"]
    audio_map = {}

    if tts_tasks and state_module.kokoro:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_idx = {
                executor.submit(
                    state_module.kokoro.create,
                    t["text"],
                    voice=voice,
                    speed=speed,
                    lang=lang,
                ): t["index"]
                for t in tts_tasks
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    samples, _ = future.result()
                    audio_map[idx] = samples.flatten()
                except Exception as e:
                    print(f"Segment {idx} failed: {e}")
                    audio_map[idx] = None

    final_segments = []
    for item in plan:
        if item["type"] == "silence":
            pause_samples = int((item["ms"] / 1000.0) * sample_rate)
            if pause_samples > 0:
                final_segments.append(np.zeros(pause_samples, dtype=np.float32))
        elif item["type"] == "tts":
            audio = audio_map.get(item["index"])
            if audio is not None:
                final_segments.append(audio)

    if final_segments:
        return safe_concat(final_segments), sample_rate
    return np.zeros(int(sample_rate * 0.1), dtype=np.float32), sample_rate


def generate_cache_key(text, voice, speed, pause_settings, rules, ignore_list):
    lang = get_language_from_voice(voice)
    cache_data = {
        "text": text,
        "voice": voice,
        "language": lang,
        "speed": speed,
        "pause_settings": pause_settings,
        "rules": [str(r) for r in rules],
        "ignore_list": sorted(ignore_list),
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_string.encode("utf-8")).hexdigest()


# --- API Endpoints ---


@router.get("/api/voices/available")
async def get_voices():
    import app.state as state_module

    if not state_module.kokoro:
        return {"categories": {}}

    try:
        raw_voices = state_module.kokoro.get_voices()

        # Group into categories
        categories = {}

        # Helper to get easy readable name
        def get_voice_name(vid):
            # e.g. af_bella -> Bella
            parts = vid.split("_")
            if len(parts) > 1:
                return parts[1].title()
            return vid

        # Helper for language labels
        def get_lang_label(code):
            maps = {
                "en-us": "English (US)",
                "en-gb": "English (UK)",
                "fr-fr": "French",
                "es": "Spanish",
                "cmn": "Chinese (Mandarin)",
                "it": "Italian",
                "pt-br": "Portuguese (Brazil)",
                "ja": "Japanese",
            }
            return maps.get(code, "Other")

        for voice in raw_voices:
            # Assuming voice is just a string ID based on previous code usage.
            # If it's an object, we adjust. Kokoro usually returns list of strings.
            voice_id = voice if isinstance(voice, str) else voice.get("id")

            # Filter out voices with Indian accents as requested (handles prefixes like v0_alpha)
            if voice_id.lower().split("_")[-1] in ["alpha", "beta", "omega", "psi"]:
                continue

            lang_code = get_language_from_voice(voice_id)
            label = get_lang_label(lang_code)

            if lang_code not in categories:
                categories[lang_code] = {"label": label, "voices": []}

            categories[lang_code]["voices"].append(
                {"id": voice_id, "name": get_voice_name(voice_id)}
            )

        # Sort voices within categories
        for code in categories:
            categories[code]["voices"].sort(key=lambda x: x["name"])

        return {"categories": categories}

    except Exception as e:
        # print(f"[DEBUG] Error processing voices: {e}")
        return {"categories": {}}


@router.get("/api/locale/{lang}")
async def get_locale(lang: str):
    locale_dir = base_dir / "locales"
    file_path = locale_dir / f"{lang}.json"
    if not file_path.exists():
        file_path = locale_dir / "en.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@router.post("/api/synthesize")
async def synthesize(request: SynthesisRequest):
    import app.state as state_module

    if state_module.kokoro is None:
        raise HTTPException(status_code=503, detail="TTS Engine not initialized.")

    try:
        text = filter_text_for_tts(request.text)
        rules_data = [r.model_dump() for r in request.rules]
        text = apply_custom_pronunciations(text, rules_data, request.ignore_list)
    except Exception:
        text = filter_text_for_tts(request.text)

    try:
        voices = state_module.kokoro.get_voices()
        selected_voice = request.voice if request.voice in voices else "af_sky"
        pause_settings = request.pause_settings or {}

        cache_key = generate_cache_key(
            text,
            selected_voice,
            float(request.speed or 1.0),
            pause_settings,
            request.rules,
            request.ignore_list,
        )

        cached_audio = audio_cache.get(cache_key)
        if cached_audio:
            return StreamingResponse(
                io.BytesIO(cached_audio),
                media_type="audio/wav",
                headers={"Content-Length": str(len(cached_audio))},
            )

        has_pause_settings = pause_settings and isinstance(pause_settings, dict)
        punctuation_chars = [
            ",",
            ".",
            "!",
            "?",
            ":",
            ";",
            "\n",
            "。",
            "，",
            "！",
            "？",
            "：",
            "；",
            "、",
        ]
        has_punctuation = any(p in text for p in punctuation_chars)
        lang = get_language_from_voice(selected_voice)

        if not re.search(
            r"[a-zA-Z0-9\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]",
            text,
        ):
            samples = np.zeros(int(24000 * 0.1), dtype=np.float32)
            sample_rate = 24000
        else:
            if has_pause_settings and has_punctuation:
                samples, sample_rate = synthesize_with_pauses(
                    text, selected_voice, float(request.speed or 1.0), pause_settings
                )
            else:
                samples, sample_rate = state_module.kokoro.create(
                    text,
                    voice=selected_voice,
                    speed=float(request.speed or 1.0),
                    lang=lang,
                )

        buffer = io.BytesIO()
        sf.write(buffer, samples.flatten(), sample_rate, format="WAV", subtype="PCM_16")
        audio_bytes = buffer.getvalue()

        audio_cache.put(cache_key, audio_bytes)

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={"Content-Length": str(len(audio_bytes))},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
