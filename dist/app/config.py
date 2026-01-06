from pathlib import Path
import os
import sys


# CRITICAL: Path Anchoring Functions
def get_app_anchored_path(relative_path: str) -> Path:
    """
    Returns a guaranteed absolute path relative to THIS script file.
    Immune to where the user launched the terminal from.
    """
    # Get the app root (parent of app/ directory)
    # This file is inside dist/app/config.py, so parent is dist/app/, parent.parent is dist/
    script_dir = Path(__file__).parent.absolute()
    app_root = script_dir.parent

    # Join and resolve to absolute path
    return (app_root / relative_path).absolute()


# Base directories
base_dir = Path(__file__).parent.absolute()
userdata_dir = get_app_anchored_path("userdata")
content_dir = userdata_dir / "content"
cache_db_path = userdata_dir / "audio_cache.db"

# File paths
settings_file = userdata_dir / "settings.json"
library_file = userdata_dir / "library.json"

# Settings
MAX_CACHE_SIZE_MB = 200

# Ensure directories exist
try:
    userdata_dir.mkdir(exist_ok=True)
    content_dir.mkdir(exist_ok=True)
except Exception as e:
    print(f"[CRITICAL] Failed to create storage dirs: {e}")
