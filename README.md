# LocalReader Pro v1.5

**A modern, privacy-focused PDF/EPUB reader with AI-powered text-to-speech, smart content detection, and MP3 export.**

---

## 🚀 What's New in v1.5

### 🧠 Smart Content Detection
- **Smart Start (Auto-Skip Intro):** Automatically skips blank pages and front matter to jump to the first page with real content (>500 characters)
- **Smart Header/Footer Filter:** Detects and removes/dims repeated headers (book titles, chapter names) and footers (page numbers) that appear on every page
  - **Three Modes:** Off, Clean (remove), or Dim (show faded)
  - **TTS-Aware:** Voice skips filtered content in all modes
  - **90% Similarity Detection:** Works even with OCR errors or typos

### 🔍 Global Search (Ctrl+F Replacement)
- **Full-Book Search:** Search across ALL pages (not just current page like browser Ctrl+F)
- **Smart Highlighting:** Yellow highlights show exact matches on the page
- **Context Previews:** See 50 characters before/after each match
- **Keyboard Shortcuts:** `Ctrl+F` (or `Cmd+F` on Mac) to open, `ESC` to close
- **Instant Navigation:** Click any result to jump to that page with highlights

### 🎨 UI/UX Enhancements
- **Sticky Header:** Page navigation and search controls stay fixed at top while scrolling
- **Draggable Sidebar:** Resize sidebar by dragging the right edge (200px-600px)
- **Full Sentence Display:** Player bar shows complete sentences without truncation
- **Centered Player Bar:** Player dynamically centers in reading pane (not entire screen)

---

## ✨ Complete Feature List

### 📚 Core Reading Features
- **Multi-Format Support:** PDF and EPUB files
- **8 Premium Voices:** American (Sky, Bella, Nicole, Sarah, Adam, Michael) and British (Isabella, Lewis)
- **Fast TTS Engine:** Kokoro-82M (~5x real-time synthesis speed)
- **Auto-Save Progress:** Resume exactly where you left off (page + sentence)
- **Sentence-Level Control:** Click any sentence to start reading from there
- **Bidirectional Smart Scroll:** Scroll down to next page, scroll up to previous page
- **Keyboard Shortcuts:** 
  - `Space` = Play/Pause
  - `←` = Previous Sentence
  - `→` = Next Sentence
  - `Ctrl+F` / `Cmd+F` = Search
  - `ESC` = Close Search

### 🧠 Smart Features (v1.5)
- **Smart Start:** Auto-skip blank/cover pages on first open
- **Header/Footer Filter:** Detect and remove/dim repeated page clutter
- **Global Search:** Full-book search with instant navigation
- **Smart Pagination:** Auto-scroll to next/previous page at boundaries

### 🎙️ TTS & Voice Control
- **Speed Control:** 0.5x to 3.0x playback speed
- **Custom Pronunciation Rules:** 
  - Fix mispronunciations (e.g., "ChatGPT" → "Chat G P T")
  - RegEx support for advanced patterns
  - Match Case and Whole Word options
  - Collapsible accordion UI for managing 100+ rules
- **Ignore List:** Skip unwanted text patterns (URLs, citations, etc.)
- **Header/Footer Awareness:** Voice skips detected noise

### 🎵 MP3 Export
- **One-Click Export:** Convert entire document to MP3
- **Background Processing:** UI stays responsive during export
- **Smart Time Estimation:** Shows ~15 seconds per 1,000 characters
- **Real-Time Progress:** Paragraph-by-paragraph tracking
- **On-Demand FFMPEG:** Auto-downloads encoder (~100MB) on first export
- **One-Click Folder Access:** Open export location in file explorer
- **Output Format:** `{document_name}_{voice_name}.mp3`

### 🎨 Modern UI
- **Dark Mode:** Easy on the eyes for long reading sessions
- **Glass Morphism Player:** Modern floating controls with backdrop blur
- **Responsive Layout:** Perfect on mobile, tablet, desktop, and ultrawide
- **Centered Reading Mode:** Optimal 900px width prevents eye fatigue
- **Draggable Sidebar:** Resize to your preference (saved to localStorage)
- **Sticky Header:** Controls always accessible while scrolling

### 🔒 Privacy & Performance
- **100% Offline:** No internet required after initial setup
- **Local Storage:** All data stays on your machine
- **No Telemetry:** Zero tracking or analytics
- **Memory Leak Prevention:** Stable during long reading sessions (~500MB)
- **70% Faster Sentence Highlighting:** DOM caching optimization
- **Crash Prevention:** Defensive bounds checks and error handling

---

## 📦 Installation

### Prerequisites
**Python 3.10 - 3.13** (Recommended: **Python 3.12**)

> ⚠️ **Important:** Python 3.14+ is not yet supported due to `onnxruntime` compatibility.

---

### Step 1: Install Python

1. **Download Python:**
   - [Python 3.12.10 (Recommended)](https://www.python.org/downloads/release/python-31210/)
   - Choose **"Windows installer (64-bit)"**

2. **Run Installer:**
   - ✅ **CRITICAL:** Check **"Add Python to PATH"** at the bottom
   - Click **"Install Now"**

3. **Verify Installation:**
   ```bash
   python --version
   ```
   Expected output: `Python 3.12.10` (or similar)

---

### Step 2: Install Dependencies

1. **Open Terminal:**
   - Press `Win + R`, type `cmd`, press Enter
   - Or right-click in the project folder → "Open in Terminal"

2. **Navigate to Project Folder:**
   ```bash
   cd "C:\path\to\LocalReader_Pro_v1.5"
   ```

3. **Install Python Packages:**
   
   **Option A - If `pip` is in PATH (recommended):**
   ```bash
   pip install -r requirements.txt
   ```

   **Option B - If you get "pip is not recognized":**
   ```bash
   python -m pip install -r requirements.txt
   ```

   This will install:
   - FastAPI (web framework)
   - uvicorn (web server)
   - torch (PyTorch for ML)
   - kokoro-onnx (TTS engine)
   - pydub (audio processing)
   - pywebview (desktop wrapper)
   - And other dependencies

4. **Wait for Installation:**
   - First install may take 5-10 minutes (downloading PyTorch ~2GB)
   - Subsequent installs are faster (uses cache)

---

### Step 3: Launch the App

**Option A: Double-Click Launcher (Windows - Recommended)**
```
📁 Double-click: launch.vbs
```
✅ Silent execution (no console window)  
✅ Works from Desktop shortcuts  
✅ Auto-pathing (no "file not found" errors)

**Option B: Command Line**
```bash
python main.py
```
Or if Python is not in PATH:
```bash
C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe main.py
```

---

### Step 4: First-Time Setup

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

---

### Step 5: First MP3 Export (Optional)

When you first try to export audio:

1. Click **"Export Audio (MP3)"** in sidebar
2. Prompt appears: "Download FFMPEG encoder (~100MB)"
3. Click **"Download FFMPEG"** and wait ~2-3 minutes
4. Export starts automatically after download
5. Subsequent exports skip this step (FFMPEG cached in `bin/` folder)

---

## 🎯 Usage Guide

### Basic Reading

1. **Upload Book:** Click "Upload Book (PDF/EPUB)" in sidebar
2. **Navigate:** 
   - Use page navigation buttons (◀ ▶) at top
   - Or scroll to bottom/top to auto-flip pages
   - Or type page number and press Enter
3. **Play Audio:** Click play button or press `Space`
4. **Jump to Sentence:** Click any sentence in the text
5. **Change Voice:** Use dropdown in sidebar settings
6. **Adjust Speed:** Drag speed slider (0.5x - 3.0x)

---

### Smart Features (v1.5)

#### Smart Start
- **Automatic:** Activates on first open of any document
- **Detection:** Finds first page with >500 characters or >100 words
- **Notification:** Toast shows "⚡ Skipped to start of content (Page X)"
- **One-Time:** Only applies on first load (respects saved position after)

#### Header/Footer Filter
1. Open **Settings** section in sidebar
2. Find **"Header/Footer Filter"** dropdown
3. Choose mode:
   - **Off:** Show everything (default)
   - **Clean:** Completely remove headers/footers
   - **Dim:** Show faded (50% opacity) but TTS skips them
4. Changes apply instantly to current page

#### Global Search
1. **Open Search:** Press `Ctrl+F` (or `Cmd+F` on Mac) or click 🔍 icon
2. **Type Query:** Minimum 2 characters
3. **Browse Results:** Shows page number, match count, and context
4. **Jump to Match:** Click any result
5. **View Highlights:** Yellow highlights show all matches on page
6. **Close Search:** Press `ESC` or click X button

---

### Custom Pronunciation Rules

Perfect for technical terms, names, acronyms, or mispronunciations.

1. **Open Rules Tab:** Click **"Pronunciation"** tab in sidebar
2. **Add Rule:** Click **+** button
3. **Configure Rule:**
   - **Original Text:** The text to replace (e.g., "SQL")
   - **Replacement Text:** How to pronounce (e.g., "S Q L" or "sequel")
4. **Options:**
   - ☑️ **Match Case:** "SQL" ≠ "sql"
   - ☑️ **Whole Word:** "cat" won't match "category"
   - ☑️ **Use Pattern Matching:** Enable RegEx (e.g., `\d{4}` for years)
5. **Save:** Click **"Done"** to collapse rule
6. **Edit:** Click any rule to expand and edit
7. **Delete:** Click trash icon in expanded view

**Example Rules:**
- `ChatGPT` → `Chat G P T` (spell out)
- `COVID-19` → `COVID nineteen` (pronounce naturally)
- `\d{4}` → `year` (RegEx: replace 4-digit numbers with "year")

---

### Ignore List

Skip unwanted text patterns entirely.

1. **Open Ignore Tab:** Click **"Ignore"** tab in sidebar
2. **Add Pattern:** Click **+** button
3. **Enter Pattern:** Type text or RegEx to skip (e.g., `https://`)
4. **Save:** Changes auto-save
5. **Delete:** Click X to remove pattern

**Common Use Cases:**
- `Figure \d+` (skip figure captions)
- `http` (skip URLs)
- `[Citation needed]` (skip wiki markup)

---

### Exporting to MP3

Convert entire documents to audio files.

1. **Open Document:** Load any PDF/EPUB
2. **Start Export:** Click **"Export Audio (MP3)"** button
3. **Review Estimate:** Check time estimate (e.g., "~3 minutes")
4. **Confirm:** Click OK in confirmation dialog
5. **Monitor Progress:** Watch real-time paragraph count
6. **Complete:** Click **"📂 Open Folder"** to access file

**Export Details:**
- **Format:** MP3, 192 kbps
- **Naming:** `{document_name}_{voice_name}.mp3`
- **Location:** `userdata/` folder in project directory
- **Speed:** ~15 seconds processing per 1,000 characters
- **During Export:** Play button disabled (prevents audio conflicts)

---

### Resizing Sidebar

1. **Hover:** Move mouse to right edge of sidebar
2. **Blue Line:** Drag handle appears (4px wide)
3. **Drag:** Click and drag left/right
4. **Release:** Width saves automatically to localStorage
5. **Range:** 200px (minimum) to 600px (maximum)

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

---

### File Structure

```
LocalReader_Pro_v1.5/
├── launch.vbs                  # Silent Windows launcher (recommended)
├── main.py                     # Entry point (starts server + webview)
├── requirements.txt            # Python dependencies
│
├── app/
│   ├── server.py               # FastAPI backend + API routes
│   ├── logic/
│   │   ├── text_normalizer.py        # Pronunciation rule engine
│   │   ├── smart_content_detector.py # Smart Start & Header/Footer filter
│   │   ├── downloader.py             # Model downloader
│   │   └── dependency_manager.py     # FFMPEG installer
│   └── ui/
│       ├── index.html          # Main SPA (Single Page App)
│       └── lib/                # Offline dependencies
│           ├── pdf.min.js      # PDF.js (Mozilla)
│           ├── pdf.worker.min.js
│           └── lucide.min.js   # Icons
│
├── bin/                        # FFMPEG binaries (auto-downloaded on first export)
│   ├── ffmpeg.exe
│   └── ffprobe.exe
│
├── userdata/                   # User data (auto-created)
│   ├── library.json            # Document library metadata
│   ├── settings.json           # User preferences (voice, speed, rules)
│   ├── content/                # Cached page content (one file per document)
│   └── *.mp3                   # Exported audio files
│
└── models/                     # Kokoro-82M models (auto-downloaded on first run)
    └── kokoro-v0_19.onnx       # ~309MB
```

---

### Performance Benchmarks

| Metric | Value |
|--------|-------|
| **TTS Speed** | ~5x real-time (300 words/min synthesis) |
| **Export Speed** | ~15 seconds per 1,000 characters |
| **Memory (Idle)** | ~100MB |
| **Memory (Model Loaded)** | ~500MB (stable, no leaks) |
| **Startup Time** | <5 seconds (model already downloaded) |
| **Smart Start Scan** | <100ms (first 10 pages) |
| **Header/Footer Detection** | ~50ms per page load |
| **Search Speed** | <500ms for 500-page book |
| **Sentence Highlighting** | 70% faster (DOM caching, v1.4.6+) |

---

### Storage Requirements

| Component | Size |
|-----------|------|
| **App Files** | ~10MB |
| **Python Dependencies** | ~2GB (PyTorch, etc.) |
| **Kokoro-82M Model** | ~309MB |
| **FFMPEG** | ~100MB (optional, for MP3 export) |
| **Per Document Cache** | ~1-5MB (depending on page count) |
| **Exported MP3** | ~1MB per minute of audio |

**Total:** ~2.5GB (without exported audio)

---

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10+ | Windows 11 |
| **Python** | 3.10 - 3.13 | 3.12.10 |
| **RAM** | 4GB | 8GB+ |
| **Disk Space** | 3GB free | 5GB+ free |
| **CPU** | Dual-core 2.0GHz | Quad-core 2.5GHz+ |
| **Internet** | Required for setup only | Offline after setup |

---

## 🔧 Troubleshooting

### Installation Issues

#### "pip is not recognized"
```bash
# Solution: Use python -m pip instead
python -m pip install -r requirements.txt

# Or use full Python path
C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
```

#### "Python was not found"
- Reinstall Python with **"Add Python to PATH"** checked
- Or find Python location and use full path:
  ```bash
  C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe main.py
  ```

#### "ERROR: ResolutionImpossible" (onnxruntime)
- You have Python 3.14+, which is not yet supported
- **Solution:** Uninstall Python 3.14 and install Python 3.12.10

#### "UnicodeEncodeError" when running
```bash
# Solution: Set UTF-8 encoding
$env:PYTHONIOENCODING="utf-8"
python main.py
```

#### Slow pip install / hanging
- Clear pip cache:
  ```bash
  pip cache purge
  ```
- Then retry:
  ```bash
  pip install -r requirements.txt
  ```

---

### Runtime Issues

#### "Voice Engine Failed to Load"
- **Check RAM:** Ensure ~500MB free memory
- **Check Internet:** First-time download requires connection
- **Re-download Model:**
  1. Delete `models/` folder
  2. Restart app
  3. Click "Setup Voice Engine"

#### App Won't Start / "File not found"
- Use `launch.vbs` instead of terminal
- If using shortcuts, point to project directory
- Check Python version: `python --version` (need 3.10-3.13)

#### Sticky Header Not Working / Controls Scroll Away
- Clear browser cache (Ctrl+Shift+R)
- Restart the app
- Verify you're on v1.5 (check window title)

#### Auto-Scroll to Next Page Broken
- v1.5 fixed this (scroll container architecture)
- If still broken, check `index.html` line ~1485 for `scrollContainer.addEventListener`

#### Search Not Highlighting / Highlights Disappear
- v1.5 improved this (re-applies highlights on page change)
- Try closing and reopening search modal
- Search only works when document is loaded

---

### Export Issues

#### Export Stuck at 0%
- **Check Permissions:** Ensure `userdata/` folder is writable
- **Check FFMPEG:** Verify `bin/ffmpeg.exe` exists
- **Restart Export:** Click Cancel and try again

#### "FFMPEG Download Failed"
- **Check Internet:** Download requires connection (~100MB)
- **Manual Install:**
  1. Download from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
  2. Extract `ffmpeg.exe` and `ffprobe.exe` to `bin/` folder

#### "Open Folder" Does Nothing
- **Check Exports:** Verify files exist in `userdata/` folder
- **Open Manually:** Navigate to project folder → `userdata/`

---

### Audio Issues

#### No Sound During Playback
- **Check Output Device:** Windows sound settings (correct speaker/headset selected)
- **Close Conflicting Apps:** Discord, Zoom, Teams (may lock audio device)
- **Restart App:** Close and relaunch LocalReader

#### Playback Stuttering / Lag
- **Check CPU Usage:** Close other heavy apps
- **Check RAM:** Ensure >1GB free memory
- **Reduce Speed:** Try 1.0x instead of 3.0x

#### Voice Sounds Robotic / Garbled
- **Re-download Model:**
  1. Delete `models/` folder
  2. Restart app
  3. Click "Setup Voice Engine"
- **Check Disk Space:** Ensure >1GB free

---

### Performance Issues

#### Slow Page Loading (Large PDFs)
- **First Load:** 500+ page PDFs take ~10-30 seconds initially
- **Subsequent Loads:** Much faster (pages cached in `userdata/content/`)
- **Solution:** Be patient on first load, or split large PDFs

#### High Memory Usage
- **Expected:** ~500MB with model loaded
- **If Higher:** Close and relaunch app (memory leak v1.4.6+ should be fixed)

#### UI Lag / Slow Sentence Highlighting
- **v1.4.6+ Fix:** 70% faster via DOM caching
- **If Still Slow:** Try shorter documents (split into chapters)

---

### Header/Footer Filter Issues

#### Filter Not Detecting Headers/Footers
- **Minimum 3 Pages:** Filter needs 3+ consecutive pages for pattern matching
- **90% Similarity:** Some variation is OK, but highly unique headers may not match
- **Manual Ignore:** Use Ignore List for specific patterns

#### Filter Removing Important Text
- **Switch to Dim Mode:** Shows text faded instead of removing
- **Turn Off:** Set mode to "Off" in settings
- **Report Issue:** May need adjustment to detection algorithm

---

## 📝 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `←` | Previous Sentence |
| `→` | Next Sentence |
| `Ctrl+F` / `Cmd+F` | Open Search |
| `ESC` | Close Search |

> **Note:** Shortcuts disabled when typing in input fields (rules, ignore list, search box)

---

## 🛡️ Privacy & Security

### Data Storage
- **100% Local:** All documents, settings, and exports stored on your machine
- **No Cloud:** Zero data sent to external servers
- **No Accounts:** No login, no sign-up, no user tracking

### Network Usage
- **Setup Only:** Internet required for:
  1. Downloading Kokoro-82M model (~309MB, first run)
  2. Downloading FFMPEG (~100MB, first export)
- **Fully Offline:** After setup, works without internet indefinitely

### Analytics & Telemetry
- **Zero Tracking:** No Google Analytics, no usage stats, no crash reports
- **No Cookies:** Web UI runs locally (no cookies stored)
- **No Logs:** App doesn't phone home or log usage data

### File Access
- **Read-Only Documents:** PDFs/EPUBs are only read (never modified)
- **Writable Folders:** Only `userdata/`, `models/`, and `bin/` (all local)
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

See `requirements.txt` and library documentation for full license details.

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

## 🔄 Version History

### v1.5 (December 2025)
- ✨ Smart Start (auto-skip intro pages)
- ✨ Smart Header/Footer Filter (3 modes)
- ✨ Global Search (Ctrl+F replacement)
- ✨ Sticky Header (always visible navigation)
- ✨ Draggable Sidebar (200px-600px)
- ✨ Full Sentence Display (no truncation)
- 🐛 Fixed nested scroll container issue
- 🐛 Fixed search highlights persistence

### v1.4 (December 2025)
- ✨ MP3 Export Feature
- ✨ On-Demand FFMPEG Downloader
- ✨ Collapsible Pronunciation Rules
- ✨ Centered Reading Mode (900px)
- ✨ Glass Morphism Player
- ⚡ 70% Faster Sentence Highlighting
- ⚡ Memory Leak Prevention
- 🐛 Fixed path issues with shortcuts
- 🐛 Fixed array bounds crashes

---

## 📞 Support

### Found a Bug?
1. Check **Troubleshooting** section above
2. Verify you're on latest version (v1.5)
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

**Version:** 1.5  
**Engine:** Kokoro-82M (ONNX)  
**Last Updated:** December 2025  
**Status:** ✅ Stable Release

---

**Enjoy your reading! 📚✨**
