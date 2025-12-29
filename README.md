# LocalReader Pro v1.4

**A modern, privacy-focused PDF/EPUB reader with AI-powered text-to-speech and MP3 export.**

## 🚀 What's New in v1.4

### 🎨 Redesigned UI & Reading Experience
- **Centered Reading Mode:** Optimal 900px width prevents eye fatigue
- **Responsive Layout:** Perfect on mobile, tablet, desktop, and ultrawide
- **Glass Morphism Player:** Modern floating controls with backdrop blur
- **Collapsible Rules:** Clean accordion interface for pronunciation rules
- **Smart Sidebar:** Auto-collapses on mobile, scales on desktop

### 🎵 MP3 Export Feature
- **Export entire documents** to high-quality MP3 files
- **Real-time progress tracking** with visual feedback
- **Smart time estimation** based on document length
- **Background processing** keeps UI responsive
- **On-demand FFMPEG download** (~100MB, one-time only)
- **One-click folder access** after export completes
- Output format: `{document_name}_{voice_name}.mp3`

### ⚡ Performance & Stability
- **70% faster** sentence highlighting on long pages (DOM caching)
- **Memory leak fixes** prevent growth during long sessions
- **Error handling** with user-friendly toast notifications
- **Crash prevention** through defensive array bounds checks
- **Debounced rendering** reduces CPU usage and visual flicker
- **Clean shutdown** with automatic resource cleanup

### 🚀 Launch Improvements
- **Silent Launcher:** `launch.vbs` runs without console window
- **Shortcut-Safe:** Works correctly from Desktop or Start Menu
- **Auto-Pathing:** No more "File not found" errors from shortcuts

## ✨ Features

### Core Functionality
- 📚 **Multi-Format Support**: PDF and EPUB files
- 🎙️ **8 Premium Voices**: American, British, Male & Female options
- ⚡ **Fast Processing**: Kokoro-82M engine (~5x real-time speed)
- 💾 **Auto-Save Progress**: Resume exactly where you left off
- 🎯 **Sentence-Level Control**: Click any sentence to jump to it
- ⌨️ **Keyboard Shortcuts**: Space (play/pause), Arrow keys (navigate)

### Advanced Features
- 🔧 **Custom Pronunciation Rules**: Fix mispronunciations with regex support
- 🚫 **Ignore List**: Skip unwanted text patterns
- 🎚️ **Speed Control**: 0.5x to 3.0x playback speed
- 📄 **Smart Pagination**: Auto-scroll to next page
- 🌙 **Dark Mode**: Easy on the eyes for long reading sessions

## 📦 Installation

---

## 🐍 Python & Pip Setup Instructions

To run LocalReader Pro, you need Python installed on your Windows machine. Follow these steps to get everything ready:

### 1. Download and Install Python
- **Link:** [Download Python 3.12 (Recommended)](https://www.python.org/downloads/windows/)
- **Installation Steps:**
    1.  Run the downloaded installer.
    2.  **CRITICAL:** Check the box that says **"Add Python to PATH"** at the bottom of the first screen.
    3.  Select "Install Now".

### 2. Verify Installation
Open a terminal (Press `Win + R`, type `cmd`, and hit Enter) and type:
```bash
python --version
pip --version
```
If you see version numbers, you are ready!

### 3. Install Dependencies
Navigate to the project folder in your terminal and run:
```bash
pip install -r requirements.txt
```
*Note: If `pip` is not recognized, try `python -m pip install -r requirements.txt`.*

---
### Setup
```bash
# 1. Clone or extract to your desired location
cd LocalReader-Pro-main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app

# Option A: Double-click (Windows)
launch.vbs

# Option B: Command line
python main.py
```

**Recommended:** Use `launch.vbs` on Windows for:
- ✅ Silent execution (no console window)
- ✅ Automatic working directory setup
- ✅ Shortcut-friendly (works from Desktop/Start Menu)

### First Run
1. Click **"Setup Voice Engine"** to download Kokoro-82M model (~309MB)
2. Wait for green status indicator
3. Upload your first PDF/EPUB

### First Export (MP3 Feature)
When you first try to export audio:
1. Click **"Export Audio (MP3)"**
2. The app will prompt to download FFMPEG (~100MB)
3. Click **"Download FFMPEG"** and wait ~2-3 minutes
4. Export will start automatically after download completes
5. Subsequent exports skip this step (FFMPEG cached locally)

## 🎯 Usage Guide

### Basic Reading
1. **Upload**: Click "Upload Book (PDF/EPUB)" in sidebar
2. **Navigate**: Use page controls or scroll to flip pages
3. **Play**: Hit the blue play button or press `Space`
4. **Jump**: Click any sentence to start reading from there

### Pronunciation Rules
1. Switch to **Rules** tab in sidebar
2. Click **+** to add a new rule
3. Enter:
   - **Original Text**: The text to replace (e.g., "ChatGPT")
   - **Replacement Text**: How to pronounce it (e.g., "Chat G P T")
4. Choose options:
   - ☑️ **Match Case**: "ChatGPT" ≠ "chatgpt"
   - ☑️ **Whole Word**: "cat" won't match "category"
   - ☑️ **RegEx**: Use patterns like `\d{4}` to match years

### Exporting to MP3
1. Open a document
2. Click **"Export Audio (MP3)"** in sidebar
3. Review estimated time and confirm
4. Monitor progress in modal window
5. Download when complete

**Note**: During export, playback is disabled to prevent audio conflicts.

## ⚙️ Technical Details

### Architecture
- **Frontend**: Vanilla JavaScript + Tailwind CSS
- **Backend**: FastAPI (Python)
- **TTS Engine**: Kokoro-82M (ONNX)
- **Desktop Wrapper**: pywebview
- **Audio Processing**: pydub + soundfile

### File Structure
```
LocalReader-Pro-main/
├── launch.vbs             # Silent launcher (double-click)
├── main.py                # Entry point (CLI)
├── requirements.txt       # Python dependencies
├── app/
│   ├── server.py          # FastAPI backend
│   ├── ui/
│   │   ├── index.html     # Main UI
│   │   └── lib/           # Offline dependencies (PDF.js, Lucide)
│   └── logic/
│       ├── text_normalizer.py
│       ├── downloader.py
│       └── dependency_manager.py  # FFMPEG on-demand installer
├── bin/                   # FFMPEG binaries (auto-downloaded)
│   ├── ffmpeg.exe
│   └── ffprobe.exe
├── userdata/              # Your library & exports
│   ├── library.json
│   ├── settings.json
│   ├── content/           # Document pages (cached)
│   └── *.mp3             # Exported audio files
└── models/                # Kokoro-82M (auto-downloaded ~309MB)
```

### Performance
- **Synthesis Speed**: ~5x real-time (Kokoro-82M)
- **Export Speed**: ~15 seconds per 1,000 characters
- **Memory Usage**: ~500MB (model loaded, stable with leak prevention)
- **Storage**: ~309MB for models + ~100MB for FFMPEG + document cache
- **UI Responsiveness**: 70% faster sentence highlighting (DOM caching)
- **Startup Time**: <5 seconds on modern hardware

## 🔧 Troubleshooting

### "Voice Engine Failed to Load"
- Ensure you have ~500MB free RAM
- Check internet connection (first-time download)
- Re-run setup: Delete `models/` folder and click "Setup Voice Engine"

### App Won't Start / "File not found"
- Use `launch.vbs` instead of running from terminal
- If using shortcuts, ensure they point to the correct directory
- Check Python is installed: `python --version` (need 3.10+)

### Export Stuck at 0%
- Check `userdata/` folder permissions (should be writable)
- Ensure FFMPEG downloaded correctly (check `bin/` folder)
- Try canceling and restarting the export

### Audio Playback Issues
- Close other apps using audio devices (Discord, Zoom, etc.)
- Check Windows sound settings (output device selected)
- Try restarting the application

### Performance Issues on Long Documents
- Large PDFs (500+ pages) may take time to load initially
- Close other browser tabs if using significant RAM
- Performance improves significantly after first page load (caching)

## 📝 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `←` | Previous Sentence |
| `→` | Next Sentence |

## 🛡️ Privacy

- **100% Offline**: No internet required after setup
- **Local Storage**: All data stays on your machine
- **No Telemetry**: Zero tracking or analytics

## 📄 License

This project uses:
- **Kokoro-82M**: Apache 2.0 License
- **Dependencies**: Various open-source licenses (see requirements.txt)

## 🙏 Credits

- **TTS Engine**: [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) by hexgrad
- **UI Framework**: [Tailwind CSS](https://tailwindcss.com/)
- **Icons**: [Lucide](https://lucide.dev/)

---

**Version**: 1.4  
**Engine**: Kokoro-82M (ONNX)  
**Last Updated**: December 2025



