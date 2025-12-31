import os
import shutil
import requests
from huggingface_hub import hf_hub_download
from typing import Literal

def download_kokoro_model(model_type: Literal["gpu", "cpu"] = "gpu") -> None:
    """
    Download the specified TTS model (Standard or Quantized).
    
    Args:
        model_type: "gpu" (standard FP32, ~309MB) or "cpu" (quantized Int8, ~87MB)
    """
    # Target directory: backend/models/
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
    os.makedirs(target_dir, exist_ok=True)

    print(f"--- LocalReader Downloader (Dual-Engine) ---")
    print(f"Target: {target_dir}")
    print(f"Mode: {model_type.upper()}\n")

    # Determine model configuration
    if model_type == "cpu":
        model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.int8.onnx"
        model_dest = os.path.join(target_dir, "kokoro.int8.onnx")
        model_label = "Quantized CPU Model (Int8)"
        model_size = "~87MB"
    else:  # "gpu"
        model_repo = "onnx-community/Kokoro-82M-v1.0-ONNX"
        model_remote_path = "onnx/model.onnx"
        model_dest = os.path.join(target_dir, "kokoro.onnx")
        model_label = "Standard GPU Model (FP32)"
        model_size = "~309MB"

    # Download Model
    if not os.path.exists(model_dest):
        print(f"Downloading {model_label} ({model_size})...")
        try:
            if model_type == "cpu":
                # Direct download from GitHub releases
                print(f"  Starting download from: {model_url}")
                r = requests.get(model_url, stream=True, timeout=300)  # 5 min timeout for large file
                r.raise_for_status()
                
                total_size = int(r.headers.get('content-length', 0))
                total_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
                downloaded = 0
                
                print(f"  Total size: {total_size_mb:.1f} MB")
                
                with open(model_dest, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # Progress indicator
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                downloaded_mb = downloaded / (1024 * 1024)
                                print(f"  Progress: {progress:.1f}% ({downloaded_mb:.1f}/{total_size_mb:.1f} MB)", end='\r')
                
                print(f"\n  [OK] {model_label} saved as kokoro.int8.onnx")
            else:
                # HuggingFace download for GPU model
                path = hf_hub_download(repo_id=model_repo, filename=model_remote_path, local_dir=target_dir)
                
                # hf_hub_download with local_dir might put it in target_dir/onnx/model.onnx
                downloaded_file = os.path.join(target_dir, "onnx", "model.onnx")
                if os.path.exists(downloaded_file):
                    shutil.move(downloaded_file, model_dest)
                    print(f"{model_label} saved as kokoro.onnx")
                elif os.path.exists(path) and path != model_dest:
                    shutil.copy2(path, model_dest)
                    print(f"{model_label} saved as kokoro.onnx")
        except Exception as e:
            print(f"Model download failed: {e}")
            raise
    else:
        print(f"{model_label} already exists.")

    # Download Voices (Shared resource - only download if missing)
    voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
    voices_dest = os.path.join(target_dir, "voices.bin")
    
    if not os.path.exists(voices_dest):
        print(f"\nDownloading Voice Pack (shared resource)...")
        try:
            r = requests.get(voices_url, stream=True, timeout=60)
            r.raise_for_status()
            
            with open(voices_dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print("Voice Pack saved as voices.bin")
            
            # Remove old voices.json to avoid confusion
            old_json = os.path.join(target_dir, "voices.json")
            if os.path.exists(old_json):
                os.remove(old_json)
        except Exception as e:
            print(f"Voice Pack download failed: {e}")
            raise
    else:
        print("Voice Pack already exists (shared between both engines).")

    # Final Cleanup
    onnx_folder = os.path.join(target_dir, "onnx")
    if os.path.exists(onnx_folder):
        shutil.rmtree(onnx_folder)
    
    print(f"\nDownload complete! Active mode: {model_type.upper()}")
    print(f"Run 'python main.py' to start.")

def check_model_exists(model_type: Literal["gpu", "cpu"]) -> bool:
    """Check if a specific model type exists."""
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
    
    if model_type == "cpu":
        model_path = os.path.join(target_dir, "kokoro.int8.onnx")
    else:
        model_path = os.path.join(target_dir, "kokoro.onnx")
    
    return os.path.exists(model_path)

def get_available_models() -> dict:
    """Return which models are currently downloaded."""
    return {
        "gpu": check_model_exists("gpu"),
        "cpu": check_model_exists("cpu"),
        "voices": os.path.exists(os.path.join(os.path.dirname(__file__), "..", "models", "voices.bin"))
    }

if __name__ == "__main__":
    import sys
    model_type = sys.argv[1] if len(sys.argv) > 1 else "gpu"
    if model_type not in ["gpu", "cpu"]:
        print("Usage: python downloader.py [gpu|cpu]")
        print("  gpu: Standard model (~309MB, best quality)")
        print("  cpu: Quantized model (~87MB, faster, low RAM)")
        sys.exit(1)
    download_kokoro_model(model_type)
