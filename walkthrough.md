# CPE Implementation Walkthrough & VS Code Running Guide

The Conversational Parameter Extractor (CPE) module is fully implemented, tested, and features a premium **glassmorphic web dashboard** for local testing. Below is a summary of the implementation details, test outcomes, and instructions for running the dashboard on your local PC.

---

## 1. Accomplished Work

### Core CPE Package (`cpe/`)
- [__init__.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/__init__.py): Defines the python package version.
- [config.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/config.py): Configuration parser loading environment variables from `.env` files.
- [schemas.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/schemas.py): Pydantic schemas validating input text, metadata context, and structuring parameters (emotional_valency, emotional_arousal, cognitive_load, academic_stress, explicit_symptoms, inferred_risks, and confidence scores).
- [text_parser.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/text_parser.py): Cleans conversational transcripts (removing tags like `Student:`, deleting filler/disfluency words like `um`, `uh`, `like`, `you know` while keeping proper punctuation) and calculates semantic density, word repetition index, and linguistic markers.
- [asr.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/asr.py): Whisper audio transcriber using `faster-whisper` (with fallback to `openai-whisper`), extracting audio duration, active speaking time, and **Pause Density** silences.
- [llm.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/llm.py): Prompt generator and API adapter (compatible with LLaMA-3-8B-Instruct via Ollama, local LLaMA.cpp, Groq, or GitHub Models API) supporting heuristic JSON repairing and automated low-temperature retry logic. Implements **Chain-of-Thought (CoT)** reasoning steps and an offline-ready **Smart Mock Mode** for immediate out-of-the-box local testing.
- [db.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/db.py): SQLite database manager using SQLAlchemy to create the `cpe_extractions` table and run background tasks to wipe transcripts older than 24 hours to enforce privacy.
- [main.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/main.py): FastAPI backend providing health status, text parameter extraction, audio parameter extraction, and cache purging. Mounted with StaticFiles to host the dashboard automatically.

### Interactive Frontend Dashboard (`frontend/`)
We have added a dedicated folder for the web-based testing UI:
- [index.html](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/frontend/index.html): HTML5 structure with text inputs, drag-and-drop audio uploading, metadata toggles, and layout grids. Features new risk cards for Academic Stress, Somatic Symptoms (Explicit), and Inferred Risks.
- [style.css](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/frontend/style.css): Premium glassmorphic styles, dark mode gradient backdrops, floating glows, letter-spaced logo designs, slider tracks, step progress indicators, and hover animations.
- [app.js](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/frontend/app.js): Dashboard controller handling tab changes, preset scenarios loading, drag-and-drop files (supporting `.wav`, `.mp3`, `.m4a`, `.mp4`, `.ogg`), API HTTP requests, and dynamic UI updates.

### Startup & Config Files
- [run_server.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/run_server.py): Command-line script to boot up the FastAPI server via Uvicorn.
- [Dockerfile](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/Dockerfile): Docker containerization script pre-packaging FFmpeg system tools and Whisper weights caching.
- [vercel.json](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/vercel.json) & [.vercelignore](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/.vercelignore): Excludes backend directories from Vercel compilation to deployment.
- [.env](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/.env): Local configuration file populated with default offline/development settings.
- [requirements.txt](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/requirements.txt): Lists all required Python packages.

---

## 2. Test Verification Outcomes

Running `python -m pytest -v` successfully executed all parser unit tests and FastAPI integration tests:
```powershell
tests/test_integration.py::test_health_check PASSED                      [ 14%]
tests/test_integration.py::test_extract_from_text PASSED                 [ 28%]
tests/test_integration.py::test_custom_heuristics PASSED                 [ 42%]
tests/test_integration.py::test_somatic_explicit_vs_inferred_and_causal_stress PASSED [ 57%]
tests/test_parser.py::test_clean_transcript_disfluencies PASSED          [ 71%]
tests/test_parser.py::test_clean_transcript_speaker_tags PASSED          [ 85%]
tests/test_parser.py::test_calculate_metrics PASSED                      [100%]

======================== 7 passed, 1 warning in 0.72s =========================
```

---

## 3. Guide to Run Locally on VS Code

Follow these steps to run, test, and query the CPE engine inside VS Code on your Windows PC:

### Step 1: Open the CPE Folder in VS Code
1. Open VS Code.
2. Select **File -> Open Folder...** and navigate to:
   `c:\Users\Tejendra Singh\Desktop\Sarthi_Summer_Intern\Wellmate-Web\backend\Engines\CPE`
3. Open a terminal panel in VS Code (**Terminal -> New Terminal** or `Ctrl + Shift + \``).

### Step 2: Set Up Python Virtual Environment
To isolate dependencies, run the following in the VS Code terminal:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
Run the command to install the requirements:
```powershell
pip install -r requirements.txt
```

### Step 4: Start the FastAPI Server
Run the startup script in the VS Code terminal:
```powershell
python run_server.py
```
You will see output indicating the server is running:
`INFO:     Uvicorn running on http://127.0.0.1:8000`

### Step 5: Open the Interactive Dashboard
1. Open your web browser.
2. Go to: **`http://localhost:8000/`** (or open your Vercel deployment link **`https://conversational-parameter-extracto-w.vercel.app/`** which will route commands directly to your local port 8000).
3. Test using presets or audio files (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.ogg`).
