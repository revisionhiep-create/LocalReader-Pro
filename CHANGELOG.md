# Changelog - LocalReader Pro v1.2

## [1.2.0] - 2025-12-28

### Added
- **Bidirectional Smart Scroll:** You can now flip to the next page by scrolling down at the bottom, or the previous page by scrolling up at the top. 
    - The voice engine automatically stops when you flip pages via scroll.
    - Backward navigation automatically scrolls to the bottom of the previous page for seamless reading continuity.
- **Dynamic Voice Engine Setup:** The "Setup Voice Engine" button now transitions to a "Downloading..." state with a spinner when clicked.
- **Contextual Upload Button:** The "Upload PDF" button is now hidden while the voice engine requires setup or is downloading, providing a cleaner UX.
- **Architectural Tools:** Integrated `backup_manager.py`, `code_scanner.py`, and `mock_server.py` into `.ai_engineer/tools/` for easier maintenance.

### Optimized
- **DOM Performance:** Re-implemented list rendering (Library, Rules, Ignore List, Sentences) using `DocumentFragment` to reduce layout thrashing.
- **Backend Imports:** Cleaned up unused imports (`time`) and moved global constants (`MAX_PHONEME_LENGTH`, `SAMPLE_RATE`) to the top level in `server.py`.
- **Status Polling:** Optimized the frontend polling loop to only update UI elements when the system state actually changes, reducing unnecessary Lucide icon regenerations.

### Fixed
- **Library UI Scaling:** Fixed an issue where long file names would overflow or scale incorrectly in the library list. Items now use `break-words` and flexible height.
- **Restore Delete Button:** Re-implemented the "X" button in the library list to allow deleting PDFs from the local storage.
- **Version Tracking:** Updated all application titles and API metadata to reflect v1.2.

