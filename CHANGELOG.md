# Changelog - LocalReader Pro

## [1.3.0] - 2025-12-28

### Added
- **EPUB Support:** Native support for .epub files. The application now includes an internal conversion pipeline that automatically transforms EPUBs into PDFs during upload for a unified reading experience.
- **Keyboard Shortcuts:** Enhanced playback control with global hotkeys:
    - **Spacebar:** Toggle Play/Pause (with smart focus-detection to allow typing).
    - **ArrowRight:** Skip to the next sentence (auto-advances pages).
    - **ArrowLeft:** Skip to the previous sentence.
- **Persistent Settings:** User preferences for **Voice Selection** and **Narration Speed** are now saved to the backend file system (`userdata/settings.json`) and restored automatically on launch.
- **Polling Voice Initialization:** Implemented a robust initialization sequence that waits for the system voice list to be ready before applying saved preferences, eliminating startup race conditions.

### Changed
- **Audio Precision:** The narration speed controller now supports `0.05x` increments (expanded range: 0.50x - 3.00x) with a consistent 2-decimal display (e.g., `1.05x`).
- **UI Branding:** Synchronized all application titles, API metadata, and headers to reflect the **v1.3 Pro Edition** status.
- **Upload Flow:** Updated the upload button text to "Upload Book (PDF/EPUB)" and expanded the file picker to accept both formats.

### Fixed
- **Glass Wall Bug:** Resolved a critical UI issue where the TTS highlight overlay blocked manual mouse-driven text selection.
- **Navigation Unresponsiveness:** Fixed a bug where the Previous/Next media buttons in the floating controller were inactive.
- **Path Mismatch:** Unified the settings loader and saver to use a single source of truth on the disk, resolving a discrepancy between write/read paths.
- **Filename Sanitization:** Hardened the EPUB conversion pipeline to handle files with illegal OS characters safely.

---

## [1.2.0] - 2025-12-28

### Added
- **Bidirectional Smart Scroll:** You can now flip to the next page by scrolling down at the bottom, or the previous page by scrolling up at the top. 
- **Dynamic Voice Engine Setup:** The "Setup Voice Engine" button now transitions to a "Downloading..." state with a spinner.
- **Contextual Upload Button:** The "Upload PDF" button is now hidden while the voice engine requires setup.
