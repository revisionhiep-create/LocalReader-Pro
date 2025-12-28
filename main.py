import os
import sys
import threading
import time
import socket
import uvicorn
import webview
from pathlib import Path

# Add the app directory to sys.path
base_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(base_dir))

from app.server import app

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def run_server():
    """Runs the FastAPI server."""
    try:
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"Server error: {e}")

def main():
    # 1. Start backend server in a daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. Wait for server to be responsive
    retries = 10
    while retries > 0:
        if is_port_in_use(8000):
            break
        time.sleep(1)
        retries -= 1

    # 3. Create the main window
    window = webview.create_window(
        'LocalReader Pro v1.3',
        url='http://127.0.0.1:8000',
        width=1200,
        height=800,
        background_color='#000000',
        min_size=(1000, 700)
    )

    # 4. Storage Path - isolated for this version
    storage_path = os.path.join(str(base_dir), 'webview_data')
    
    # 5. Start the UI loop
    webview.start(debug=False, storage_path=storage_path)

    # 6. Shutdown
    os._exit(0)

if __name__ == "__main__":
    main()
