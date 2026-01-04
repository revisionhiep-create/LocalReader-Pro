# LocalReader Pro Changelog

## v2.7 - January 4, 2026

### 🎨 UI/UX & Visual Polish
- **Dark Mode Refinement:** Updated the "Export Audio" button to a more sophisticated **Deep Indigo** (`#4B0082`) to improve contrast and visual hierarchy in dark mode.
- **Improved Sidebar Feedback:** UI elements like the "Export" button and the new "Text Size" slider now dynamically show/hide based on document state and engine readiness.

### ✨ New Features
- **Audio Player Text Resizing:** Added a **"Text Size" Slider** in the sidebar. This allows users to dynamically resize the subtitle/caption text in the bottom player bar (Range: 12px to 24px) for better accessibility and focus.
- **Smart Line Height:** Caption text now automatically adjusts its line height alongside font size for optimal readability.

### 🔧 Persistence & Reliability
- **Persistent Voice Selection:** Fixed a long-standing bug where the chosen voice (e.g., `am_adam`) would reset to the default after app restart. Selection is now saved to disk and restored even after dynamic voice list refreshes.
- **Global Settings Audit:** Unified persistence for all user preferences including:
  - **Voice ID**
  - **Playback Speed**
  - **Player Text Size**
  - **Pause Settings**
  - **UI Language**
- **Settings Data Integrity:** Added `font_size` to the backend settings model and implemented atomic writes to prevent configuration corruption.

### 📦 Maintenance
- **Cleanup:** Removed deprecated `setup.exe` from the distribution to encourage direct Python execution/portable use.

---

## v2.6 - January 4, 2026

# LocalReader Pro v2.5 Changelog

## v2.5 - January 3, 2026

### 🇨🇳 Chinese Language Support (Full Integration)
- **New Voice:** Added **Chinese (Mandarin)** voice support (`zf_xiaobei`, `zf_xiaomi`, etc.) powered by Kokoro-82M.
- **UI Translation:** Fully translated the interface into **Simplified Chinese (简体中文)**.
- **Smart Punctuation Logic:**
  - Added support for **Full-width Punctuation**: `，` (comma), `。` (period), `！` (exclamation), `？` (question).
  - These symbols now correctly trigger the custom pause durations set in the Settings drawer.
  - **Sentence Splitting:** Fixed an issue where Chinese paragraphs were treated as single massive sentences (causing "Index 510" token errors). The engine now correctly splits by `。` `！` `？`.
- **Layout Fixes:**
  - **No Extra Spaces:** Fixed a bug where the PDF converter inserted spaces between Chinese characters (`你 好` → `你好`).
  - **Terminal Detection:** Improved paragraph detection to prevent merging lines ending in Chinese punctuation.

### 🌍 Multilingual Architecture Overhaul
- **Dynamic Voice Loading:**
  - The voice list is no longer hardcoded. It now **dynamically fetches** available voices from the backend based on the loaded model.
  - Voices are automatically grouped by language (English, French, Spanish, Chinese, etc.) in the dropdown.
- **Language Codes:** Standardized internal language codes to match `espeak-ng` (`cmn`, `it`, `pt-br`, `fr-fr`, `en-us`).
- **New Languages Enabled:**
  - **Italian** (`if_sara`, `im_nicola`)
  - **Portuguese (Brazil)** (`pf_dora`, `pm_alex`)
  - *(Note: These require the Multilingual Voice Pack)*

### 🛠️ Core Improvements
- **Self-Healing Audio Cache:**
  - The SQLite audio cache (`audio_cache.db`) now automatically detects corruption or missing tables and rebuilds itself without crashing the app.
  - Added robust checks before every read/write operation.
- **UI Localization:**
  - Fixed missing translations for:
    - **Processing Mode:** "High Quality (GPU)" / "High Performance (CPU)"
    - **Voice Drawer:** "Playback Speed", "Header/Footer Filter"
    - **Pause Settings:** All slider labels are now translated.

### 🐛 Bug Fixes
- **Fixed:** "Index 510 is out of bounds" error when processing long Chinese/Japanese paragraphs.
- **Fixed:** Japanese text sometimes hallucinating "In Chinese" (Reverted unstable experimental logic).
- **Fixed:** Layout issues where CJK characters were wrapped with unnecessary whitespace.

---

## v2.3.0 - January 1, 2026

### 🧠 Smart Pause Logic Overhaul (Detailed Breakdown)

**1. Punctuation Group Handling ("The Ellipsis Fix")**
- **Problem:** Previous versions treated `...` as three separate periods, tripling the pause time (e.g., 600ms × 3 = 1.8s). Or, if filtered, it resulted in 0ms.
- **New Logic:** The engine now detects consecutive punctuation groups (e.g., `...`, `?!`, `!!`) as a single event.
- **Mechanism:** It inspects the **last character** of the group to determine the pause type.
  - `Wait...` → Uses `.` setting (Period Pause)
  - `Really?!` → Uses `!` setting (Exclamation Pause)
  - `Hello??` → Uses `?` setting (Question Pause)

**2. Smart Newline Handling ("The Flow Fix")**
- **Problem:** Previous versions stripped newlines to prevent audio gaps, causing text to "rush" together.
- **New Logic:** Newlines are preserved but handled conditionally based on context.
- **State Tracking:** The engine remembers if the previous segment was punctuation.
  - **Scenario A (Paragraphs):** Text ends with punctuation (`End.
`).
    - *Action:* The newline pause is **SKIPPED** to prevent stacking with the period pause.
  - **Scenario B (Headers/Titles):** Text has no punctuation (`Chapter One
`).
    - *Action:* A **"Soft Pause"** (default 300ms) is applied. This separates headers from body text without needing manual punctuation.

**3. Implementation Details**
- **Regex Update:** Text is split using `([,.
!?:;]+|
)`, ensuring delimiters are captured but separated.
- **Fallback Safety:** If no specific newline setting is provided, it defaults to 300ms (minimum "breathing room") rather than 0ms.

### 🚀 Performance & Stability
- Maintained all v2.2 caching improvements (SQLite + Prefetching)
- Optimized regex segmentation for cleaner audio stitching

---

## v2.2.1 - January 1, 2026

### 🚀 Performance Improvements
- **FIXED**: Eliminated 5-10 second audio delay when switching pages
- **Implemented**: Cross-page prefetching system
  - TTS now pre-generates first sentence of next page while reading current page
  - Page transitions reduced from 5-10s to <500ms
  - Seamless audio playback across page boundaries
- **Technical**: Modified `preCacheNextSentences()` to parse and cache next page's first sentence

### 🎯 User Experience
- Smooth continuous reading without interruptions
- No more waiting when auto-advancing to new pages
- Background prefetch doesn't block current playback

---

## ✨ What's New in v2.2

### 🗄️ SQLite Audio Cache
- **Replaced:** File-based `.cache/` directory with `audio_cache.db` SQLite database
- **Storage:** WAV audio stored as BLOB in database
- **Size Limit:** 200MB (increased from v2.0's 100MB)
- **Eviction:** LRU (Least Recently Used) automatic cleanup when size limit exceeded
- **Performance:** Instant cache lookups, no file system overhead

### 📁 Cache Management
- **Location:** `userdata/audio_cache.db`
- **Structure:**
  - `cache_key` (TEXT PRIMARY KEY): MD5 hash of TTS parameters
  - `audio_data` (BLOB): WAV file bytes
  - `size_bytes` (INTEGER): File size for LRU tracking
  - `created_at` (REAL): Creation timestamp
  - `accessed_at` (REAL): Last access timestamp (LRU)

### 🔧 Implementation Details
- **New File:** `app/logic/audio_cache.py` - SQLite cache manager class
- **Modified File:** `app/server.py` - Integrated SQLite cache
- **Removed:** Old file-based cache functions (lines 79-221 in original v2.0)

---

## 📊 Cache Behavior

### When Cache Hits:
1. Query SQLite by `cache_key`
2. Update `accessed_at` timestamp (LRU tracking)
3. Return audio BLOB from memory
4. Stream to client

### When Cache Misses:
1. Generate audio with Kokoro TTS
2. Convert to WAV bytes
3. Insert into SQLite with current timestamp
4. Trigger cleanup if size > 200MB
5. Stream to client

### LRU Cleanup Logic:
- Triggered automatically when inserting new audio
- Sorts all entries by `accessed_at` (oldest first)
- Deletes oldest entries until total size ≤ 200MB
- Logs deleted count and new size

---

## 🧪 Testing Results

### ✅ Startup Verification
- Server starts successfully on `http://127.0.0.1:8000`
- SQLite database created at `userdata/audio_cache.db` (16KB initial size)
- No errors in startup logs

### ✅ UI Verification
- Language toggle working (ES button visible and functional)
- All UI elements rendering correctly
- No console errors in browser

### 🔄 Migration from v2.0
If you have an existing v2.0 installation with file-based cache:
1. Old `.cache/*.wav` files will NOT be migrated (fresh cache)
2. SQLite database will be created on first TTS request
3. Cache will rebuild naturally as you use the app

---

## 🎯 Why SQLite vs Files?

| Feature | v2.0 (Files) | v2.2 (SQLite) |
|---------|--------------|---------------|
| Cache Lookups | O(n) glob scan | O(1) indexed query |
| LRU Tracking | File `st_atime` | Database timestamp |
| Size Calculation | Sum all file sizes | Single SQL query |
| Cleanup Speed | Delete files one-by-one | Single transaction |
| Portability | Platform-dependent paths | Single .db file |
| Atomicity | No guarantees | ACID transactions |

---

## 🚀 Performance Impact

**Expected Improvements:**
- Faster cache lookups (no file system scan)
- More reliable LRU eviction (precise timestamp tracking)
- Simpler backup (single .db file)
- No file descriptor limits (all in-memory ops)

**Trade-offs:**
- Slightly larger disk usage (SQLite overhead ~16KB)
- Cannot manually browse cached audio files (binary BLOB)

---

### 🐛 Bug Fixes

- **Fixed MP3 Export:** Export now captures **full book content** instead of just chapter headers
  - **Root Cause:** Pages were treated as single chunks, exceeding `MAX_PHONEME_LENGTH` (~500 chars) and getting truncated
  - **Solution:** Split pages into paragraphs and sentences, ensuring each chunk stays under 500 chars
  - **Result:** All content exported, not just first ~500 characters of each page
- **Removed "Clear Audio Cache" button** from UI (SQLite cache manages itself automatically)

---

## 📝 Notes

- Based on working v2.0 architecture (Python backend, vanilla UI)
- All v2.0 features preserved (multilingual TTS, pronunciation rules, smart start, etc.)
- Cache database grows dynamically up to 200MB, then auto-cleans
- Language UI bug from v2.1 avoided by using clean v2.0 base

---

**Date:** January 3, 2026  
**Status:** ✅ Stable
