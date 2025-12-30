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
FFMPEG_EXE = BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = BIN_DIR / "ffprobe.exe"

# Stable FFMPEG build from Gyan.dev
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
        """Check if FFMPEG binaries are already installed"""
        return FFMPEG_EXE.exists() and FFPROBE_EXE.exists()
    
    def cancel(self):
        """Cancel the download process"""
        self.is_cancelled = True
    
    def install(self) -> tuple[bool, Optional[str]]:
        """
        Download and install FFMPEG binaries.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
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

def get_ffmpeg_path() -> Optional[str]:
    """
    Get the path to the local FFMPEG executable.
    Returns None if not installed.
    """
    if FFMPEG_EXE.exists():
        return str(FFMPEG_EXE)
    return None

def get_ffprobe_path() -> Optional[str]:
    """
    Get the path to the local FFPROBE executable.
    Returns None if not installed.
    """
    if FFPROBE_EXE.exists():
        return str(FFPROBE_EXE)
    return None

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

