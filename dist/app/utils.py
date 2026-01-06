import json
from pathlib import Path
from typing import Any


def safe_save_json(path: Path, data: Any):
    """Atomic write to prevent corruption"""
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        json.dump(data, f)
    temp_path.replace(path)


def safe_init_json(path: Path, default_data: Any):
    """Initialize JSON file if it doesn't exist"""
    if not path.exists():
        with open(path, "w") as f:
            json.dump(default_data, f)


def get_language_from_voice(voice: str) -> str:
    """
    Detect language from voice ID prefix.
    Returns appropriate language code for Kokoro TTS.
    """
    if voice.startswith(("af_", "am_")):
        return "en-us"
    elif voice.startswith(("bf_", "bm_")):
        return "en-gb"
    elif voice.startswith(("ff_", "fm_")):
        return "fr-fr"
    elif voice.startswith(("ef_", "em_")):
        return "es"
    elif voice.startswith(("zf_", "zm_")):
        return "cmn"
    elif voice.startswith(("if_", "im_")):
        return "it"
    elif voice.startswith(("pf_", "pm_")):
        return "pt-br"
    elif voice.startswith(("jf_", "jm_")):
        return "ja"
    else:
        return "en-us"
