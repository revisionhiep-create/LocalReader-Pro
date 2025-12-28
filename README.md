# LocalReader Pro v1.2 🚀

LocalReader Pro is a standalone, privacy-focused desktop application designed for a premium PDF reading and Text-to-Speech (TTS) experience. Everything runs 100% locally on your machine—no data ever leaves your computer.

---

## 🌟 Full Feature List

### 🎙️ Advanced Local TTS
- **High-Quality AI Engine:** Powered by the Kokoro-82M ONNX model for natural-sounding, offline speech synthesis.
- **Multiple Voices:** Choose from a variety of voices, including AF Bella, AF Sky, AM Adam, and more (US & British accents).
- **Adjustable Speed:** Fine-tune playback speed from 0.5x to 2.0x in real-time.
- **Punctuation Awareness:** Gracefully handles non-speakable characters and provides natural pauses.

### 📖 Premium Reading Experience
- **Bidirectional Smart Scroll:** Navigate through your books naturally using your mouse wheel. Scroll down at the bottom to flip to the next page; scroll up at the top to go back.
- **Voice Engine Auto-Stop:** Scrolling to a new page automatically stops the voice engine to ensure the audio matches what you see on screen.
- **Smart Sentence Merging:** Automatically joins fragmented lines and fixes common PDF extraction artifacts for smoother listening.
- **Coordinate-Aware Extraction:** Intelligent text extraction that filters out "ghost spaces" and "hidden text" used in some PDFs to block copying.
- **Ligature Normalization:** Correctly handles special characters like `ﬀ` and `ﬁ` for accurate pronunciation.

### 🗂️ Library & Persistence
- **Integrated PDF Library:** Manage multiple books with ease. Includes a "Delete" button (X) to remove books you've finished.
- **Auto-Saving Progress:** Your current page and sentence are saved automatically the moment you stop reading.
- **Server-Side Settings:** Pronunciation rules and ignore lists are stored locally in `userdata/settings.json`, ensuring your preferences persist across updates and restarts.
- **Atomic File Saves:** Uses robust save logic to prevent data corruption.

### 🛠️ Customization
- **Custom Pronunciation Rules:** Create rules to fix how specific words are pronounced (e.g., "PDF" -> "Portable Document Format"). Supports "Match Case" and "Word Boundary" modes.
- **Ignore List:** Skip specific words or characters globally during playback (e.g., page numbers or watermarks).

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

## 🚀 How to Use LocalReader

1.  **Launch the App:** Double-click `LocalReader.bat` or run `python main.py`.
2.  **Initial Setup:** If you are running the app for the first time, click the **"Setup Voice Engine"** button. The app will download the necessary AI models (approx. 350MB).
3.  **Upload a PDF:** Once the engine is ready, the **"Upload PDF"** button will appear. Select any PDF from your computer.
4.  **Start Reading:**
    *   Click any sentence to start reading from that point.
    *   Use the **Play/Pause** button at the bottom to control playback.
    *   Use the **Skip Back/Forward** buttons to move between sentences.
5.  **Manage Settings:**
    *   Use the **Rules** tab to add pronunciation fixes.
    *   Use the **Ignore** tab to skip recurring text you don't want to hear.
    *   Switch **Voices** or adjust **Speed** using the controls in the sidebar.

---

## 🏗️ Architecture
- **Wrapper:** `pywebview` (for a native desktop window)
- **Backend:** FastAPI (Python)
- **TTS Engine:** Kokoro-82M ONNX
- **Frontend:** Tailwind CSS + PDF.js + Lucide Icons
- **Storage:** Local JSON files in `userdata/`

---

## 📜 Privacy
LocalReader Pro is built with privacy as a first principle. All PDF processing and voice synthesis occur entirely on your local machine. No analytics, no tracking, and no cloud dependencies.

