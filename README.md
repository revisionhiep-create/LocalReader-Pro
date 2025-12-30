# LocalReader Pro

**A modern, privacy-focused PDF/EPUB reader with AI-powered text-to-speech, natural speech flow, and smart audio caching.**

---

## ✨ Key Features

### 📚 Core Reading
- **Multi-Format Support:** PDF and EPUB files
- **8 Premium Voices:** American (Sky, Bella, Nicole, Sarah, Adam, Michael) and British (Isabella, Lewis)
- **Fast TTS Engine:** Kokoro-82M (~5x real-time synthesis speed)
- **Auto-Save Progress:** Resume exactly where you left off
- **Sentence-Level Control:** Click any sentence to start reading from there

### 🎙️ Smart TTS Controls
- **Natural Speech Flow:** Intelligent line joining prevents mid-sentence stops
- **Custom Pause Settings:** Granular control over pause duration for each punctuation type (0-2000ms)
- **Smart Pause Logic:** Only single punctuation creates pauses (ignores "...", "?!", "!!!")
- **Custom Pronunciation Rules:** Fix mispronunciations with RegEx support
- **Speed Control:** 0.5x to 3.0x playback speed

### 🧠 Smart Features
- **Smart Start:** Auto-skip blank/cover pages on first open
- **Header/Footer Filter:** Detect and remove/dim repeated page clutter
- **Global Search:** Full-book search with instant navigation (Ctrl+F)
- **Smart Audio Caching:** 100MB LRU cache with automatic cleanup

### 🎵 MP3 Export
- **One-Click Export:** Convert entire document to MP3
- **Background Processing:** UI stays responsive during export
- **On-Demand FFMPEG:** Auto-downloads encoder (~100MB) on first export

### 🔒 Privacy & Performance
- **100% Offline:** No internet required after initial setup
- **Local Storage:** All data stays on your machine
- **No Telemetry:** Zero tracking or analytics
- **Fast Performance:** ~5x real-time synthesis, 70% faster sentence highlighting

---

## 📦 Installation

### Windows (Recommended)

**One-Click Installer - No Manual Setup Required**

1. **Extract the ZIP** to your desired location
2. **Double-click:** `Install LocalReader Pro.lnk`
3. **Approve UAC Prompt** when Windows requests administrator access
4. **Wait for Installation:**
   - Checks for Python 3.12+ (downloads and installs if missing)
   - Deploys application files
   - Installs all dependencies automatically
   - Creates Desktop and Start Menu shortcuts
5. **Launch:** Double-click "LocalReader Pro" on your Desktop

**What the installer does:**
- ✅ Installs Python 3.12 if not present
- ✅ Installs all required packages (FastAPI, PyTorch, Kokoro-TTS, etc.)
- ✅ Creates shortcuts on Desktop and Start Menu
- ✅ Sets up the application in the selected directory

**Uninstalling:**
- Run `uninstall.exe` in the installation directory
- Removes all shortcuts (application files remain for manual deletion)

**Installation Size:**
- Installer: ~24 MB
- Full installation: ~2.6 GB (including Python dependencies)

---

### Linux / Manual Installation

**Prerequisites:** Python 3.10 - 3.13 (Recommended: Python 3.12)

> ⚠️ **Important:** Python 3.14+ is not yet supported due to `onnxruntime` compatibility.

**Step 1: Install Python**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-pip python3.12-venv

# Verify installation
python3.12 --version
```

**Step 2: Extract and Navigate**

```bash
unzip LocalReader_Pro_v1.8.zip
cd LocalReader_Pro_v1.8/dist
```

**Step 3: Install Dependencies**

```bash
# Option A: Using pip
pip install -r requirements.txt

# Option B: Using python -m pip (if pip not in PATH)
python3.12 -m pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- uvicorn (web server)
- torch (PyTorch for ML)
- kokoro-onnx (TTS engine)
- pydub (audio processing)
- pywebview (desktop wrapper)
- And other dependencies

**Installation time:** 5-10 minutes (downloading PyTorch ~2GB)

**Step 4: Launch the App**

```bash
python3.12 main.py
```

---

## 🚀 First-Time Setup

After launching the application:

1. **Setup Voice Engine:**
   - Click **"Setup Voice Engine"** button in sidebar
   - Downloads Kokoro-82M model (~309MB, one-time)
   - Wait for green status indicator (⚫ → 🟢)

2. **Upload Your First Book:**
   - Click **"Upload Book (PDF/EPUB)"**
   - Select any PDF or EPUB file
   - App will process and display the book

3. **Start Reading:**
   - Click the blue **Play** button
   - Or press `Space` to play/pause

4. **First MP3 Export (Optional):**
   - Click **"Export Audio (MP3)"** in sidebar
   - Prompt appears: "Download FFMPEG encoder (~100MB)"
   - Click **"Download FFMPEG"** and wait ~2-3 minutes
   - Export starts automatically after download
   - Subsequent exports skip this step

---

## 🎯 Usage Guide

### Basic Reading

- **Navigate Pages:** Use buttons (◀ ▶) or scroll to bottom/top for auto-flip
- **Play Audio:** Press `Space` or click play button
- **Jump to Sentence:** Click any sentence in the text
- **Change Voice:** Use dropdown in sidebar settings
- **Adjust Speed:** Drag speed slider (0.5x - 3.0x)

### Smart Features

**Smart Start:**
- Automatically activates on first open
- Finds first page with >500 characters
- Shows notification: "⚡ Skipped to start of content (Page X)"

**Header/Footer Filter:**
1. Open **Settings** section in sidebar
2. Find **"Header/Footer Filter"** dropdown
3. Choose: **Off**, **Clean** (remove), or **Dim** (show faded)
4. TTS skips filtered content in all modes

**Global Search:**
1. Press `Ctrl+F` (or `Cmd+F` on Mac)
2. Type query (minimum 2 characters)
3. Click any result to jump to that page
4. Press `ESC` to close

### Custom Pronunciation Rules

1. Click **"Pronunciation"** tab in sidebar
2. Click **+** button to add rule
3. Configure:
   - **Original Text:** The text to replace (e.g., "SQL")
   - **Replacement Text:** How to pronounce (e.g., "S Q L")
4. Options:
   - ☑️ **Match Case:** "SQL" ≠ "sql"
   - ☑️ **Whole Word:** "cat" won't match "category"
   - ☑️ **Use Pattern Matching:** Enable RegEx

**Example Rules:**
- `ChatGPT` → `Chat G P T` (spell out)
- `COVID-19` → `COVID nineteen` (pronounce naturally)

### Custom Pause Settings

1. Open **"Pause Settings"** section in sidebar
2. Adjust sliders to set pause duration (0-2000ms):
   - **Comma (,)** - Default: 250ms
   - **Period (.)** - Default: 600ms
   - **Question (?)** - Default: 600ms
   - **Exclamation (!)** - Default: 600ms
   - **Colon (:)** - Default: 500ms
   - **Semicolon (;)** - Default: 500ms
   - **Newline** - Default: 800ms
3. Settings save automatically

**Smart Behavior:**
- Pauses apply only to single punctuation
- `"..."` creates NO pause (not 3× period pause)
- `"?!"` creates NO pause (natural speech flow)

### Exporting to MP3

1. Open any PDF/EPUB document
2. Click **"Export Audio (MP3)"** button
3. Review time estimate (e.g., "~3 minutes")
4. Confirm export
5. Monitor real-time progress
6. Click **"📂 Open Folder"** to access file

**Export Details:**
- **Format:** MP3, 192 kbps
- **Naming:** `{document_name}_{voice_name}.mp3`
- **Location:** `userdata/` folder in project directory
- **Speed:** ~15 seconds per 1,000 characters

---

## 📝 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `←` | Previous Sentence |
| `→` | Next Sentence |
| `Ctrl+F` / `Cmd+F` | Open Search |
| `ESC` | Close Search |

---

## ⚙️ Technical Details

### Architecture

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vanilla JavaScript + Tailwind CSS |
| **Backend** | FastAPI (Python) |
| **TTS Engine** | Kokoro-82M (ONNX Runtime) |
| **Desktop Wrapper** | pywebview |
| **PDF Parsing** | PDF.js (Mozilla) |
| **Audio Export** | pydub + FFMPEG |
| **EPUB Support** | ebooklib + xhtml2pdf |

### File Structure

```
LocalReader_Pro_v1.8/
├── Install LocalReader Pro.lnk      # Windows installer shortcut
├── Uninstall LocalReader Pro.lnk    # Uninstaller shortcut
├── README.md
├── CHANGELOG.md
│
└── dist/
    ├── setup.exe                    # One-click installer (24 MB)
    ├── main.py                      # Application entry point
    ├── launch.vbs                   # Silent Windows launcher
    ├── requirements.txt             # Python dependencies
    │
    ├── app/
    │   ├── server.py                # FastAPI backend
    │   ├── logic/
    │   │   ├── text_normalizer.py        # Pronunciation rules
    │   │   ├── smart_content_detector.py # Smart features
    │   │   ├── downloader.py             # Model downloader
    │   │   └── dependency_manager.py     # FFMPEG installer
    │   └── ui/
    │       ├── index.html           # Main SPA
    │       └── lib/                 # Offline dependencies
    │
    └── userdata/                    # User data (auto-created)
        ├── library.json             # Document library
        ├── settings.json            # Preferences
        ├── content/                 # Cached page content
        └── *.mp3                    # Exported audio
```

**Additional folders created during use:**
- `bin/` - FFMPEG binaries (auto-downloaded on first export)
- `.cache/` - Audio cache (~100MB, auto-managed)
- `models/` - Kokoro-82M model (~309MB, auto-downloaded)

### Storage Requirements

| Component | Size |
|-----------|------|
| **Installer** | ~24 MB |
| **App Files** | ~10 MB |
| **Python Dependencies** | ~2 GB (PyTorch, etc.) |
| **Kokoro-82M Model** | ~309 MB |
| **FFMPEG** | ~100 MB (optional) |
| **Audio Cache** | ~100 MB max (auto-managed) |
| **Per Document Cache** | ~1-5 MB |
| **Exported MP3** | ~1 MB per minute of audio |

**Total:** ~2.6 GB (without exported audio)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10+ / Ubuntu 20.04+ | Windows 11 / Ubuntu 22.04+ |
| **Python** | 3.10 - 3.13 | 3.12.10 |
| **RAM** | 4 GB | 8 GB+ |
| **Disk Space** | 3 GB free | 5 GB+ free |
| **CPU** | Dual-core 2.0 GHz | Quad-core 2.5 GHz+ |
| **Internet** | Required for setup only | Offline after setup |

---

## 🔧 Troubleshooting

### Windows Installation Issues

**Installer won't run / "Windows protected your PC"**
- Click "More info" → "Run anyway"
- The installer is safe (not signed with expensive code certificate)

**Python installation fails**
- Check internet connection
- Ensure ~500 MB free disk space
- Try running installer as administrator manually

**Dependencies installation stuck**
- Be patient (PyTorch download is ~2 GB)
- Check internet connection
- First install takes 5-10 minutes

**Shortcuts not created**
- Check Desktop and Start Menu manually
- Installer may need admin privileges

### Linux / Manual Installation Issues

**"pip is not recognized"**
```bash
# Solution: Use python -m pip
python3.12 -m pip install -r requirements.txt
```

**"Python was not found"**
```bash
# Find Python location
which python3.12

# Use full path
/usr/bin/python3.12 -m pip install -r requirements.txt
```

**"ERROR: ResolutionImpossible" (onnxruntime)**
- You have Python 3.14+, which is not yet supported
- Install Python 3.12 instead

**Slow pip install / hanging**
```bash
# Clear pip cache
pip cache purge

# Retry
pip install -r requirements.txt
```

### Runtime Issues

**"Voice Engine Failed to Load"**
- Check RAM: Ensure ~500 MB free memory
- Check Internet: First-time download requires connection
- Re-download Model:
  1. Delete `models/` folder
  2. Restart app
  3. Click "Setup Voice Engine"

**App Won't Start / "File not found"**
- Use `launch.vbs` instead of terminal
- Check Python version: `python --version` (need 3.10-3.13)
- Verify all files extracted from ZIP

**No Sound During Playback**
- Check output device in Windows sound settings
- Close conflicting apps (Discord, Zoom, Teams)
- Restart the app

**Export Stuck at 0%**
- Check permissions: Ensure `userdata/` folder is writable
- Check FFMPEG: Verify `bin/ffmpeg.exe` exists
- Restart export

---

## 🛡️ Privacy & Security

### Data Storage
- **100% Local:** All documents, settings, and exports stored on your machine
- **No Cloud:** Zero data sent to external servers
- **No Accounts:** No login, no sign-up, no user tracking

### Network Usage
- **Setup Only:** Internet required for:
  1. Downloading Python (Windows installer only, ~100 MB)
  2. Installing dependencies (~2 GB)
  3. Downloading Kokoro-82M model (~309 MB)
  4. Downloading FFMPEG (~100 MB, optional)
- **Fully Offline:** After setup, works without internet indefinitely

### Analytics & Telemetry
- **Zero Tracking:** No analytics, no usage stats, no crash reports
- **No Cookies:** Web UI runs locally
- **No Logs:** App doesn't phone home

### File Access
- **Read-Only Documents:** PDFs/EPUBs are only read (never modified)
- **Writable Folders:** Only `userdata/`, `models/`, `bin/`, and `.cache/`
- **No Background Access:** App closes completely when you exit

---

## 📄 License

### LocalReader Pro
- **Code:** Proprietary (review, modify, use personally)
- **Redistribution:** Contact author for permission

### Third-Party Components

| Component | License |
|-----------|---------|
| **Kokoro-82M** | Apache 2.0 |
| **FastAPI** | MIT |
| **PyTorch** | BSD-3-Clause |
| **PDF.js** | Apache 2.0 |
| **Tailwind CSS** | MIT |
| **Lucide Icons** | ISC |
| **FFMPEG** | LGPL 2.1+ |

---

## 🙏 Credits

### Core Technologies
- **TTS Engine:** [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) by hexgrad
- **PDF Rendering:** [PDF.js](https://mozilla.github.io/pdf.js/) by Mozilla
- **UI Framework:** [Tailwind CSS](https://tailwindcss.com/)
- **Icons:** [Lucide](https://lucide.dev/)
- **Audio Processing:** [FFMPEG](https://ffmpeg.org/)

### Python Libraries
- FastAPI, uvicorn, torch, onnxruntime, pydub, soundfile, pywebview, ebooklib, beautifulsoup4, and more (see `requirements.txt`)

---

## 📞 Support

### Found a Bug?
1. Check **Troubleshooting** section above
2. Verify you're on latest version (v1.8)
3. Check `CHANGELOG.md` for known issues
4. Contact developer with:
   - Python version (`python --version`)
   - Error message or screenshot
   - Steps to reproduce

### Feature Requests
- Review `CHANGELOG.md` to see if already implemented
- Describe use case and expected behavior
- Provide examples or mockups if applicable

---

**Version:** 1.8  
**Engine:** Kokoro-82M (ONNX)  
**Last Updated:** December 2025  
**Status:** ✅ Stable Release

---

**Enjoy your reading! 📚✨**
