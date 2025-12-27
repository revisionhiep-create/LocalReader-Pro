# LocalReader Pro 🚀

Standalone, privacy-focused PDF Text-to-Speech desktop application.

## Quick Start

1. **Prerequisites:**
   - **Windows 10/11**
   - **Python 3.10+**
     - [Download Python Here](https://www.python.org/downloads/)
     - ⚠️ **CRITICAL:** On the first screen of the installer, you **MUST** check the box that says **"Add Python to PATH"** before clicking Install. This enables the `pip` command to work in your terminal.

2. **Setup:**
   Open your terminal (Command Prompt or PowerShell) and run:
   ```bash
   cd LocalReader_Pro
   pip install -r requirements.txt

3. **RUN:**
   In the LocalReader_Pro folder run the command below:
   ```bash
   python main.py


## Easy Launch (One-Click)

To run the application without opening a terminal:

1. Double-click the included `LocalReader.bat` file.

## Features

* **Standalone Window:** No browser needed.
* **One-Click Setup:** Download models directly from the UI.
* **Status Indicator:** Real-time feedback on the AI engine (Red/Yellow/Green).
* **Auto-Shutdown:** Closing the window stops all background processes.
* **Local AI Engine:** Uses the Kokoro-82M model for high-quality, offline speech synthesis.
* **Portable Design:** All components are self-contained in the application folder.
* **PDF Library:** Integrated library management for uploaded PDF documents.
* **Automatic Persistence:** Saves reading progress (page and sentence) automatically.
* **Smart Start:** Automatically begins reading from page 3 for documents with 3 or more pages to skip introductory material.
* **Custom Pronunciation:** Regex-based dictionary support with "Match Case" and "Word Boundary" options.
* **Ignore List:** Global list to skip specific words, letters, or symbols during playback.
* **Playback Control:** Adjustable speed (0.5x to 2.0x) and selection of multiple male/female voices.
* **Dark Mode UI:** Default high-contrast dark interface optimized for reading.

## Architecture

* **Wrapper:** `pywebview`
* **Engine:** FastAPI + Kokoro-82M ONNX
* **UI:** Tailwind CSS + PDF.js + Dexie.js (IndexedDB)

```

```
