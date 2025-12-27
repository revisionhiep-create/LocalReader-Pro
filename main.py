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
    # 1. Check if port 8000 is already in use
    if is_port_in_use(8000):
        print("Port 8000 is already in use. Attempting to clear...")
        # On Windows, we can try to find and kill the process using this port
        try:
            import subprocess
            # Find PID using port 8000
            result = subprocess.check_output('netstat -ano | findstr :8000', shell=True).decode()
            if result:
                # Get the last column (PID) from the first line of output
                pid = result.strip().split('\n')[0].strip().split()[-1]
                if pid and pid != "0":
                    print(f"Killing existing process {pid} on port 8000...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    time.sleep(1)
        except Exception as e:
            print(f"Could not automatically clear port 8000: {e}")

    # 2. Start backend server in a daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 3. Wait for server to be responsive
    retries = 5
    while retries > 0:
        if is_port_in_use(8000):
            break
        time.sleep(1)
        retries -= 1

    # 4. Create the main window
    # We now serve via http:// to ensure IndexedDB and other web features persist correctly
    window = webview.create_window(
        'LocalReader Pro',
        url='http://127.0.0.1:8000',
        width=1200,
        height=800,
        background_color='#000000',
        min_size=(1000, 700)
    )

    # 5. Start the UI loop with persistent storage
    # On Windows, pywebview uses Edge WebView2. 
    # The 'private_mode=False' is default, but we'll be explicit.
    # We'll use the 'LocalReaderPro' folder in AppData for all browser data.
    app_data = os.environ.get('APPDATA') or os.path.expanduser('~')
    storage_path = os.path.join(app_data, 'LocalReaderPro')
    
    print(f"Starting with storage at: {storage_path}")
    webview.start(debug=False, storage_path=storage_path)

    # 6. Shutdown logic
    print("Shutting down LocalReader Pro...")
    os._exit(0) # Forcefully exit to kill daemon threads immediately

if __name__ == "__main__":
    main()

