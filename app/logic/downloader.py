import os
import shutil
import requests
from huggingface_hub import hf_hub_download

def download_kokoro_model() -> None:
    # 1. Download ONNX model (300MB+)
    # Source: onnx-community is stable for ONNX
    model_repo = "onnx-community/Kokoro-82M-v1.0-ONNX"
    model_remote_path = "onnx/model.onnx"
    
    # 2. Voices file (30MB+)
    # We MUST use the voices.bin from the kokoro-onnx releases.
    # The JSON version causes a numpy pickle error in version 0.4.9+.
    voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
    
    # Target directory: backend/models/
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
    os.makedirs(target_dir, exist_ok=True)

    print(f"--- LocalReader Downloader ---")
    print(f"Target: {target_dir}\n")

    # Download Model
    model_dest = os.path.join(target_dir, "kokoro.onnx")
    if not os.path.exists(model_dest):
        print(f"Downloading Model ({model_repo})...")
        try:
            path = hf_hub_download(repo_id=model_repo, filename=model_remote_path, local_dir=target_dir)
            # hf_hub_download with local_dir might put it in target_dir/onnx/model.onnx
            downloaded_file = os.path.join(target_dir, "onnx", "model.onnx")
            if os.path.exists(downloaded_file):
                shutil.move(downloaded_file, model_dest)
                print("Model saved as kokoro.onnx")
            elif os.path.exists(path) and path != model_dest:
                shutil.copy2(path, model_dest)
                print("Model saved as kokoro.onnx")
        except Exception as e:
            print(f"Model download failed: {e}")
    else:
        print("Model already exists.")

    # Download Voices (Overwriting voices.bin to be sure it's the right one)
    voices_dest = os.path.join(target_dir, "voices.bin")
    print(f"Downloading Voices from {voices_url}...")
    try:
        r = requests.get(voices_url, stream=True)
        if r.status_code == 200:
            with open(voices_dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Voices saved as voices.bin")
            
            # Remove old voices.json to avoid confusion
            old_json = os.path.join(target_dir, "voices.json")
            if os.path.exists(old_json):
                os.remove(old_json)
        else:
            print(f"Voices download failed (Status {r.status_code})")
    except Exception as e:
        print(f"Voices download failed: {e}")

    # Final Cleanup
    onnx_folder = os.path.join(target_dir, "onnx")
    if os.path.exists(onnx_folder):
        shutil.rmtree(onnx_folder)
    
    print(f"\nReady! Run 'python main.py' to start.")

if __name__ == "__main__":
    download_kokoro_model()
