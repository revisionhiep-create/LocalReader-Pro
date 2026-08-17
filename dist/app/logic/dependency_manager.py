"""
Dependency Manager - On-demand FFMPEG installation
Keeps the app lightweight by downloading FFMPEG only when needed for MP3 export.
"""
import os
import sys
import requests
import zipfile
import shutil
from pathlib import Path
from typing import Callable, Optional

# Determine base directory (project root)
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as script
    BASE_DIR = Path(__file__).parent.parent.parent

BIN_DIR = BASE_DIR / "bin"

# Only Windows binaries carry a .exe suffix. Keep these constant names -- other
# modules import them -- but resolve the filename per platform.
IS_WINDOWS = sys.platform == "win32"
_SUFFIX = ".exe" if IS_WINDOWS else ""
FFMPEG_EXE = BIN_DIR / f"ffmpeg{_SUFFIX}"
FFPROBE_EXE = BIN_DIR / f"ffprobe{_SUFFIX}"

# Stable FFMPEG build from Gyan.dev. Windows-only build -- see install().
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

class FFMPEGInstaller:
    """Handles automatic FFMPEG download and installation"""
    
    def __init__(self, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Args:
            progress_callback: Function called with (downloaded_bytes, total_bytes, status_message)
        """
        self.progress_callback = progress_callback
        self.is_cancelled = False
    
    def check_installed(self) -> bool:
        """True if usable ffmpeg AND ffprobe exist, bundled in bin/ or on PATH."""
        return bool(get_ffmpeg_path() and get_ffprobe_path())
    
    def cancel(self):
        """Cancel the download process"""
        self.is_cancelled = True
    
    def install(self) -> tuple[bool, Optional[str]]:
        """
        Download and install FFMPEG binaries.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        # FFMPEG_DOWNLOAD_URL is a Windows build: unpacking it on macOS/Linux
        # yields .exe files that cannot run. Use the platform's own ffmpeg there.
        if not IS_WINDOWS:
            if self.check_installed():
                self._update_progress(1, 1, "Using system FFMPEG")
                return True, None
            return False, (
                "FFmpeg was not found on this system. Install it and restart, e.g. "
                "'brew install ffmpeg' on macOS or your package manager on Linux."
            )

        try:
            # 1. Create bin directory
            BIN_DIR.mkdir(exist_ok=True)
            
            # 2. Download FFMPEG zip
            self._update_progress(0, 0, "Connecting to download server...")
            
            temp_zip = BIN_DIR / "ffmpeg_temp.zip"
            
            response = requests.get(FFMPEG_DOWNLOAD_URL, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_cancelled:
                        temp_zip.unlink(missing_ok=True)
                        return False, "Download cancelled"
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self._update_progress(downloaded, total_size, "Downloading FFMPEG...")
            
            # 3. Extract binaries
            self._update_progress(0, 1, "Extracting binaries...")
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                # Find the ffmpeg.exe and ffprobe.exe inside the zip
                # They are usually in a structure like: ffmpeg-X.X.X-essentials_build/bin/ffmpeg.exe
                ffmpeg_found = False
                ffprobe_found = False
                
                for file_info in zip_ref.namelist():
                    if file_info.endswith('bin/ffmpeg.exe'):
                        # Extract directly to our bin folder
                        with zip_ref.open(file_info) as source, open(FFMPEG_EXE, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        ffmpeg_found = True
                    elif file_info.endswith('bin/ffprobe.exe'):
                        with zip_ref.open(file_info) as source, open(FFPROBE_EXE, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        ffprobe_found = True
                    
                    if ffmpeg_found and ffprobe_found:
                        break
            
            # 4. Cleanup
            temp_zip.unlink(missing_ok=True)
            
            # 5. Verify installation
            if not (FFMPEG_EXE.exists() and FFPROBE_EXE.exists()):
                return False, "Failed to extract FFMPEG binaries"
            
            self._update_progress(1, 1, "Installation complete!")
            return True, None
            
        except requests.exceptions.RequestException as e:
            return False, f"Download failed: {str(e)}"
        except zipfile.BadZipFile:
            temp_zip.unlink(missing_ok=True)
            return False, "Downloaded file is corrupted"
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    def _update_progress(self, current: int, total: int, message: str):
        """Internal helper to call progress callback"""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, message)
            except Exception as e:
                print(f"Progress callback error: {e}")

def _resolve(bundled: Path, name: str) -> Optional[str]:
    """
    Prefer the copy in bin/, then fall back to whatever is on PATH so a
    system-managed install (Homebrew, apt, winget) works without downloading.
    Returns None if neither exists.
    """
    if bundled.exists():
        return str(bundled)
    return shutil.which(name)

def get_ffmpeg_path() -> Optional[str]:
    """Path to a usable ffmpeg, or None if not installed."""
    return _resolve(FFMPEG_EXE, "ffmpeg")

def get_ffprobe_path() -> Optional[str]:
    """Path to a usable ffprobe, or None if not installed."""
    return _resolve(FFPROBE_EXE, "ffprobe")

# Configure pydub to use local FFMPEG
def configure_pydub():
    """
    Configure pydub to use locally installed FFMPEG binaries.
    Must be called after FFMPEG is installed and before using pydub.
    """
    from pydub import AudioSegment
    
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()
    
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
    if ffprobe_path:
        AudioSegment.ffprobe = ffprobe_path

