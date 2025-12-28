# LocalReader Pro v1.3 🚀

LocalReader Pro is a standalone, privacy-focused desktop application designed for a premium PDF/EPUB reading and Text-to-Speech (TTS) experience. Everything runs 100% locally on your machine—no data ever leaves your computer.

---

## 🌟 Full Feature List

### 🎙️ Advanced Local TTS
- **High-Quality AI Engine:** Powered by the Kokoro-82M ONNX model for natural-sounding, offline speech synthesis.
- **Multiple Voices:** Choose from a variety of voices, including AF Bella, AF Sky, AM Adam, and more.
- **High-Precision Speed:** Fine-tune playback speed from 0.50x to 3.00x in **0.05x increments**.
- **Persistent Preferences:** Your favorite voice and speed are saved automatically and restored every time you launch the app.

### 📖 Premium Reading Experience
- **EPUB & PDF Support:** Seamlessly upload and read both `.pdf` and `.epub` files. EPUBs are automatically converted to PDF standard on-the-fly.
- **Bidirectional Smart Scroll:** Navigate through your books naturally using your mouse wheel. Scroll down at the bottom to flip to the next page; scroll up at the top to go back.
- **Voice Engine Auto-Stop:** Scrolling to a new page automatically stops the voice engine to ensure the audio matches what you see on screen.
- **Smart Sentence Merging:** Automatically joins fragmented lines and fixes common PDF extraction artifacts.

### 🗂️ Library & Persistence
- **Integrated Book Library:** Manage multiple books with ease. Includes "Delete" functionality for finished titles.
- **Auto-Saving Progress:** Your current page and sentence are saved automatically the moment you stop reading.
- **Unified Settings:** All configurations, including pronunciation rules and UI preferences, are stored locally in `userdata/settings.json`.

### 🛠️ Customization
- **Custom Pronunciation Rules:** Fix how specific words are pronounced (e.g., "PDF" -> "Portable Document Format").
- **Ignore List:** Skip specific words or characters globally during playback.

---

## ⌨️ Keyboard Shortcuts

Control your reading experience without using the mouse:

| Key | Action |
|-----|--------|
| **Spacebar** | Toggle Play / Pause |
| **Right Arrow** | Skip to Next Sentence |
| **Left Arrow** | Skip to Previous Sentence |

*Note: Shortcuts are disabled while typing in input fields or editing rules.*

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

---

## 🚀 How to Use LocalReader

1.  **Launch the App:** Double-click `LocalReader.bat` or run `python main.py`.
2.  **Initial Setup:** Click **"Setup Voice Engine"** to download the AI models (approx. 350MB).
3.  **Upload a Book:** Click **"Upload Book (PDF/EPUB)"** and select your file.
4.  **Start Reading:** Click any sentence or press **Spacebar**.

---

## 🏗️ Architecture
- **Wrapper:** `pywebview` (Native desktop window)
- **Backend:** FastAPI (Python)
- **TTS Engine:** Kokoro-82M ONNX
- **Frontend:** Tailwind CSS + PDF.js + Lucide Icons
- **Storage:** Local JSON files in `userdata/`

---

## 📜 Privacy
LocalReader Pro is built with privacy as a first principle. All processing and voice synthesis occur entirely on your local machine. No analytics, no tracking, and no cloud dependencies.

