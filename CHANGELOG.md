# LocalReader Pro - Changelog

## 🚀 v1.8 - One-Click Windows Installer (Dec 2025)

### Major Feature: Standalone Installer System
**Problem Solved:** Installation required manual Python setup, dependency installation, and technical knowledge.

**Solution: Bootstrapper Architecture**
- **Lightweight Installer:** 24 MB standalone `setup.exe` (doesn't bundle heavy dependencies)
- **Zero Configuration:** Installer handles everything automatically
- **Smart Deployment:** Downloads and installs only what's needed

### Installation Workflow

**What the installer does:**

1. **Admin Check:**
   - Automatically prompts Windows UAC for administrator privileges
   - Required for Python installation and system-wide setup

2. **Python 3.12 Detection:**
   - Checks if Python 3.12+ is already installed
   - If missing: Downloads official Python 3.12 installer (~100 MB)
   - Installs silently: `/quiet InstallAllUsers=1 PrependPath=1`

3. **Application Deployment:**
   - Extracts complete application to install directory
   - Deploys: `main.py`, `launch.vbs`, `app/`, `requirements.txt`, `uninstaller.py`

4. **Dependency Installation:**
   - Runs: `pip install -r requirements.txt`
   - Downloads PyTorch, FastAPI, Kokoro-TTS, and all dependencies (~2 GB)
   - May take 5-10 minutes depending on internet speed

5. **Shortcut Creation:**
   - Creates "LocalReader Pro" shortcut on Desktop
   - Creates "LocalReader Pro" shortcut in Start Menu
   - Both point to `launch.vbs` for silent execution

**Technical Implementation:**
```python
# Installer uses PyInstaller with:
--onefile              # Single executable
--noconsole            # GUI only (no console window)
--uac-admin            # Request admin automatically
--add-data             # Bundle application files
```

**Benefits:**
- ✅ **One-Click Install:** Double-click shortcut → Approve UAC → Wait → Done
- ✅ **No Technical Knowledge:** Users don't need to know about Python, pip, or terminals
- ✅ **Automatic Python:** Installs Python if missing (no manual download needed)
- ✅ **Professional UX:** Windows-native installer with UAC integration
- ✅ **Small Download:** 24 MB installer vs bundling 2 GB of dependencies
- ✅ **Smart:** Only downloads what's needed (reuses existing Python if compatible)

### Uninstaller System

**Problem Solved:** No way to cleanly remove application shortcuts.

**Solution:**
- **Uninstall Script:** Removes Desktop and Start Menu shortcuts
- **User Control:** Application files remain in install directory
- **Manual Cleanup:** Users can delete install folder if desired

**Uninstaller Features:**
- Admin prompt (required for system-wide shortcut removal)
- Confirmation dialog before uninstall
- Shows exactly what will be removed
- Displays install directory location for manual cleanup

### Distribution Structure

**Root Folder:**
```
LocalReader_Pro_v1.8/
├── Install LocalReader Pro.lnk      # Shortcut to dist/setup.exe
├── Uninstall LocalReader Pro.lnk    # Shortcut to dist/uninstall.exe  
├── README.md                        # Updated installation instructions
└── dist/
    └── setup.exe                    # 24 MB standalone installer
```

**After Installation (Install Directory):**
```
C:\Program Files\LocalReader_Pro\   (or user-selected location)
├── launch.vbs                       # Silent launcher
├── main.py                          # Application entry point
├── requirements.txt                 # Dependency list
├── uninstaller.py                   # Uninstall script
├── app/                             # Application code
├── userdata/                        # User data (auto-created)
├── models/                          # Kokoro-82M (auto-downloaded)
├── bin/                             # FFMPEG (auto-downloaded)
└── .cache/                          # Audio cache (auto-managed)
```

### User Experience Improvements

**Before (v1.7):**
1. Download Python installer separately
2. Run Python installer manually
3. Open terminal / CMD
4. Navigate to project folder
5. Run: `pip install -r requirements.txt`
6. Wait 10 minutes for dependencies
7. Create shortcuts manually
8. Run `python main.py` or `launch.vbs`

**After (v1.8):**
1. Double-click: `Install LocalReader Pro.lnk`
2. Approve UAC prompt
3. Wait 5-15 minutes (everything automated)
4. Double-click "LocalReader Pro" on Desktop

**Time Saved:** ~80% reduction in setup time and complexity

### Technical Details

**Installer Components:**
- `installer_logic.py` - Main installer logic (tkinter UI, Python detection, deployment)
- `build_installer.py` - Compiler script (PyInstaller automation)
- `uninstaller.py` - Shortcut removal script

**PyInstaller Configuration:**
- Bundled files: `requirements.txt`, `launch.vbs`, `main.py`, `app/`, `uninstaller.py`
- Excluded modules: numpy, torch, pandas, PIL, scipy (downloaded at install time)
- UAC manifest: Automatically requests admin elevation
- Size optimization: 24 MB (vs 200+ MB if dependencies bundled)

**Installer UI:**
- Built with tkinter (no external dependencies)
- Indeterminate progress bar during long operations
- Status messages: "Checking Python...", "Installing dependencies...", "Creating shortcuts..."
- Success dialog with install location

### Platform Support

**Windows:**
- ✅ Fully automated one-click installer
- ✅ UAC integration
- ✅ Shortcut creation (Desktop + Start Menu)
- ✅ Python auto-install

**Linux/macOS:**
- Manual installation (same as v1.7)
- Requires pre-installed Python 3.10-3.13
- Run: `pip install -r requirements.txt` → `python main.py`

### Installer Size Breakdown

| Component | Size |
|-----------|------|
| **Installer Executable** | 10 MB |
| **Bundled Application** | 12 MB (main.py, app/, requirements.txt) |
| **Tkinter Runtime** | 2 MB |
| **Total** | **24 MB** |

**NOT Included (Downloaded at Install Time):**
- Python 3.12 (~100 MB) - if missing
- PyTorch (~1.5 GB)
- FastAPI, uvicorn, pydub, pywebview (~400 MB)
- Kokoro-TTS (~100 MB)

### Version Updates
- Removed version numbers from UI (per Rule XIII)
- Version info now only in: README.md, CHANGELOG.md

---

## 🚀 v1.7 - Natural Speech Flow & Smart Cache Management (Dec 2025)

### Feature 1: Intelligent Pause Logic
**Problem Solved:** Consecutive punctuation (e.g., "Ah...", "What?!", "Stop!!!") created excessive, unnatural pauses during TTS playback.

**Solution:**
- **Single Punctuation Only:** Pauses applied only to isolated punctuation marks at sentence endings
- **Consecutive Ignored:** Multiple same punctuation (`...`, `!!!`, `???`) creates NO pause
- **Mixed Ignored:** Mixed punctuation (`?!`, `...!`, `?!?`) creates NO pause
- **Natural Speech:** TTS flows naturally without artificial delays

**Technical Implementation:**
```python
# Split captures punctuation sequences as single tokens
segments = re.split(r'([,\.!\?:;]+|\n)', text)

# Apply pause only if single character
if len(segment) == 1:
    # Apply configured pause (e.g., "." → 600ms)
else:
    # Skip pause entirely (e.g., "..." → ignored)
```

**Benefits:**
- ✅ **Natural Flow:** "Ah..." no longer has 3x delays
- ✅ **Simpler Logic:** No complex deduplication needed
- ✅ **Better Prosody:** TTS maintains natural rhythm
- ✅ **User Control:** Pause sliders work predictably

**Examples:**
| Text | Old Behavior | New Behavior |
|------|--------------|--------------|
| `"Hello."` | 600ms pause | 600ms pause ✅ |
| `"Ah..."` | 1800ms (3× 600ms) | **No pause** ✅ |
| `"What?!"` | 1200ms (600+600) | **No pause** ✅ |
| `"Stop!!!"` | 1800ms (3× 600ms) | **No pause** ✅ |

---

### Feature 1B: Custom Pause Settings UI
**New Feature:** Granular control over pause duration for each punctuation type.

**UI Components:**
- **Pause Settings Section:** Collapsible panel in sidebar with 7 adjustable sliders
- **Slider Range:** 0ms to 2000ms per punctuation type
- **Punctuation Types:**
  - Comma (`,`) - Default: 250ms
  - Period (`.`) - Default: 600ms
  - Question (`?`) - Default: 600ms
  - Exclamation (`!`) - Default: 600ms
  - Colon (`:`) - Default: 500ms
  - Semicolon (`;`) - Default: 500ms
  - Newline - Default: 800ms

**Benefits:**
- ✅ **Personalized Reading Speed:** Adjust to your preference (fast vs careful listening)
- ✅ **Real-Time Feedback:** Changes apply immediately to playback
- ✅ **Auto-Save:** Settings persist across sessions
- ✅ **Visual Feedback:** Slider displays current value (e.g., "250ms")
- ✅ **Smart Integration:** Works seamlessly with single-punctuation pause logic

**Use Cases:**
- **Speed Listeners:** Lower all pauses to 100-200ms for rapid audiobook experience
- **Careful Study:** Increase period/question to 800-1000ms for note-taking
- **Continuous Flow:** Set newline to 0ms to eliminate paragraph breaks
- **Natural Rhythm:** Use balanced defaults for human-like reading pace

**Technical Details:**
- Settings stored in `userdata/settings.json` under `pause_settings` object
- Backend receives settings via `POST /api/synthesize` request
- Audio stitching applies custom pause durations using pydub silent audio segments

---

### Feature 2: Natural Sentence Flow
**Problem Solved:** PDFs with line breaks mid-sentence caused abrupt audio stops and unnatural reading flow.

**Root Cause:** PDF text wrapping creates newlines in the middle of sentences, and the sentence splitter was treating each line as a separate "sentence."

**Example:**
```
Before (Broken):
"I tried to move, but my limbs felt heavy like wet"  ← Stops abruptly
"cotton."                                             ← Starts awkwardly

After (Fixed):
"I tried to move, but my limbs felt heavy like wet cotton."  ← Complete sentence
```

**Solution:**
Preprocessing logic joins lines that don't end with sentence-ending punctuation:
```javascript
// Join lines without sentence punctuation
text = text
    .replace(/\n\n/g, '<!PARAGRAPH!>')      // Preserve paragraphs
    .replace(/([^.!?:;])\n/g, '$1 ')        // Join broken lines
    .replace(/<!PARAGRAPH!>/g, '\n\n')      // Restore paragraphs
    .replace(/  +/g, ' ');                  // Clean spacing
```

**Benefits:**
- ✅ **Natural Flow:** No more abrupt mid-sentence stops
- ✅ **Better Prosody:** TTS uses proper sentence intonation
- ✅ **Visual Match:** What you see matches what you hear
- ✅ **Paragraph Support:** Double newlines preserved for future features

---

### Feature 3: Smart Audio Cache Management
**Problem Solved:** TTS audio cache accumulated indefinitely, consuming disk space without limits.

**Solution: Size-Based LRU (Least Recently Used)**
- **Size Limit:** 100MB maximum cache size (adjustable)
- **Age Limit:** Auto-delete files older than 7 days
- **LRU Strategy:** Deletes oldest-accessed files first when limit reached
- **Automatic Cleanup:** Runs on startup and before saving new files

**Technical Implementation:**
```python
# Cache Settings
MAX_CACHE_SIZE_MB = 100  # Default: 100MB
MAX_FILE_AGE_DAYS = 7    # Default: 7 days

# Cleanup on startup
def run_cache_cleanup():
    # Step 1: Delete files older than 7 days
    age_deleted = cleanup_old_cache_files()
    
    # Step 2: Delete oldest files if over 100MB (LRU)
    size_deleted = cleanup_cache_by_size()
    
    # Report: "Freed 33MB, 60 files deleted"
```

**Cleanup Triggers:**
1. **On Startup:** Full cleanup (age + size checks)
2. **Before Saving:** Checks if cache > 90MB, runs LRU cleanup if needed
3. **Future:** Manual "Clear Cache" button (optional)

**Benefits:**
- ✅ **Fast Playback:** Recently played audio loads instantly (cache hit)
- ✅ **Controlled Space:** Never exceeds 100MB
- ✅ **Smart Retention:** Keeps current book cached, removes old books
- ✅ **Zero Maintenance:** Automatic cleanup, no user action needed

**Typical Usage:**
- Short sentence: ~50-100 KB
- Long sentence: ~200-300 KB
- 300-page book: ~20-50 MB
- **100MB holds:** 2-3 full books or 1000-2000 sentences

**Console Output:**
```
[CACHE CLEANUP] Starting...
  Initial: 247 files, 132.45 MB
  Deleted 18 files older than 7 days
  Deleted 42 oldest files to fit 100MB limit
  Final: 187 files, 98.73 MB (freed 33.72 MB)
[CACHE CLEANUP] Complete

[CACHE HIT] Serving cached audio for hash abc123de...  ← Instant
[CACHE MISS] Generating audio for hash 789ghijk...     ← First time
```

---

### Feature 4: Windows Console Compatibility
**Problem Solved:** Emoji characters (✅❌🔍→) in console output caused `UnicodeEncodeError` crashes on Windows terminals.

**Solution:** Replaced all Unicode characters with ASCII equivalents:
- ✅ → `[OK]`
- ❌ → `[ERROR]`
- 🔍 → `[LOOKUP]`
- → → `=` or `to`
- 📊 → `[INFO]`
- 💾 → `[CACHE SAVE]`

**Benefits:**
- ✅ **Universal Compatibility:** Works on all Windows terminal types
- ✅ **Reliable Startup:** No more crashes during initialization
- ✅ **Clear Logging:** ASCII output still readable and professional

**Before (Crashed):**
```python
print(f"✅ Server ready on http://127.0.0.1:8000")  # UnicodeEncodeError
```

**After (Works):**
```python
print(f"[OK] Server ready on http://127.0.0.1:8000")  # Safe
```

---

### API Changes (v1.7)

**Updated Endpoints:**
- `POST /api/synthesize` - Now implements single-punctuation-only pause logic

**New Functions:**
- `get_cache_size_mb()` - Calculate total cache size
- `get_cache_file_count()` - Count cached files
- `cleanup_old_cache_files()` - Delete files older than N days
- `cleanup_cache_by_size()` - LRU cleanup to stay under size limit
- `run_cache_cleanup()` - Full cleanup routine (age + size)

**Settings Model:**
- Pause logic now checks for consecutive/mixed punctuation patterns
- Cache cleanup runs automatically on app lifespan startup

---

### Performance Notes
- **Cache Cleanup:** <100ms for typical cache (200-300 files)
- **LRU Sorting:** <50ms for access time comparison
- **Sentence Flow:** No performance impact (preprocessing is instant)
- **Pause Logic:** Simpler than deduplication (faster processing)

---

## 🚀 v1.5 - Smart Content Detection & Global Search (Dec 2025)

### Feature 1: Smart Start (Auto-Skip Intro)
**Problem Solved:** Most PDFs have useless cover pages, copyright notices, and blank pages that waste time.

**How It Works:**
1. When a book is uploaded/opened for the first time, scans the first 10 pages
2. Finds the first page with substantial content (>500 characters OR >100 words)
3. Automatically jumps to that page instead of page 1
4. Shows toast notification: "⚡ Skipped to start of content (Page X)"

**Benefits:**
- ✅ **Time Saver:** No more manual scrolling through empty pages
- ✅ **Smart Detection:** Works with any PDF structure
- ✅ **Non-Intrusive:** Only applies on first open (respects saved position)
- ✅ **Visual Feedback:** Toast notification confirms the skip

---

### Feature 2: Smart Header/Footer Filter
**Problem Solved:** Repeated headers (book title, chapter) and footers (page numbers) disrupt TTS and reading flow.

**How It Works:**
1. **Analysis Logic:**
   - Compares first 3 lines and last 3 lines with adjacent pages
   - If a line is 90%+ similar across 3 consecutive pages, flags it as "noise"
   - Detects standalone numbers (e.g., "4", "Page 5") and flags as page numbers

2. **Three Modes:**
   - **Off (Default):** No filtering, shows everything
   - **Clean:** Completely removes headers/footers from display AND TTS
   - **Dim:** Shows headers/footers faded (50% opacity, 80% size) but TTS skips them

**Benefits:**
- ✅ **Cleaner Reading:** No repeated clutter on every page
- ✅ **Better TTS:** Voice doesn't read "Chapter 5" 30 times
- ✅ **Flexible:** Choose between complete removal or visual dimming
- ✅ **Smart Detection:** Works across different PDF layouts

---

### Feature 3: Global Search (Ctrl+F Replacement)
**Problem Solved:** Browser's native Ctrl+F is useless for paginated content - it can't search pages that aren't loaded.

**How It Works:**
1. **Backend API:** Searches across ALL pages in the document
2. **Search Modal:** Floating search palette with auto-search (300ms debounce)
3. **Keyboard Shortcuts:** `Ctrl+F` / `Cmd+F` opens, `ESC` closes
4. **Smart Navigation:** Click any result → Jump to page with highlights

**Benefits:**
- ✅ **True Full-Text Search:** Searches entire book, not just current page
- ✅ **Context Preview:** See surrounding text before jumping
- ✅ **Fast Results:** Backend caches make searches instant
- ✅ **Visual Feedback:** Yellow highlights show exact matches

---

### UI 1.5: Layout Upgrades

#### 0. Sticky Header (Always Visible While Scrolling)
- Header with page navigation stays fixed at top while reading
- Controls always accessible without scrolling back up
- Smooth content scrolling underneath the header

#### 1. Draggable Sidebar (Resizable)
- Drag handle appears on sidebar's right edge
- Min 200px, Max 600px width
- Saves width to localStorage

#### 2. Player Centered in Reading Pane
- Player dynamically centers in content area (not entire screen)
- Reacts to sidebar resize automatically

#### 3. Full Sentence Display (No Truncation)
- Full sentence text displayed (no "..." truncation)
- Multi-line wrapping for long sentences
- Better readability

---

(Previous versions omitted for brevity - see full CHANGELOG in v1.7)
