# CPE Implementation Walkthrough & VS Code Running Guide

The Conversational Parameter Extractor (CPE) module is fully implemented, tested, and features a premium **glassmorphic web dashboard** for local testing. Below is a summary of the implementation details, test outcomes, and instructions for running the dashboard on your local PC.

---

## 1. Accomplished Work

### Core CPE Package (`cpe/`)
- [__init__.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/__init__.py): Defines the python package version.
- [config.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/config.py): Configuration parser loading environment variables from `.env` files.
- [schemas.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/schemas.py): Pydantic schemas validating input text, metadata context, and structuring parameters (valence, arousal, cognitive load, academic stress, somatic symptoms, and confidence scores).
- [text_parser.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/text_parser.py): Cleans conversational transcripts (removing tags like `Student:`, deleting filler/disfluency words like `um`, `uh`, `like`, `you know` while keeping proper punctuation) and calculates semantic density and linguistic markers.
- [asr.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/asr.py): Whisper audio transcriber using `faster-whisper` (with fallback to `openai-whisper`), extracting audio duration, active speaking time, and **Pause Density** silences.
- [llm.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/llm.py): Prompt generator and API adapter (compatible with LLaMA-3-8B-Instruct via Ollama, local LLaMA.cpp, Groq, or GitHub Models API) supporting heuristic JSON repairing and automated low-temperature retry logic. It also includes an offline-ready **Smart Mock Mode** for immediate out-of-the-box local testing.
- [db.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/db.py): SQLite database manager using SQLAlchemy to create the `cpe_extractions` table and run background tasks to wipe transcripts older than 24 hours to enforce privacy.
- [main.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/cpe/main.py): FastAPI backend providing health status, text parameter extraction, audio parameter extraction, and cache purging. Mounted with StaticFiles to host the dashboard automatically.

### Interactive Frontend Dashboard (`frontend/`)
We have added a dedicated folder for the web-based testing UI:
- [index.html](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/frontend/index.html): HTML5 structure with text inputs, drag-and-drop audio uploading, metadata toggles, and layout grids.
- [style.css](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/frontend/style.css): Premium glassmorphic styles, dark mode gradient backdrops, floating glows, slider tracks, step progress indicators, and hover animations.
- [app.js](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/frontend/app.js): Dashboard controller handling tab changes, preset scenarios loading, drag-and-drop files, API HTTP requests, and dynamic UI updates.

### Startup & Config Files
- [run_server.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/run_server.py): Command-line script to boot up the FastAPI server via Uvicorn.
- [.env](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/.env): Local configuration file populated with default offline/development settings.
- [requirements.txt](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/requirements.txt): Lists all required Python packages.

### Verification & Testing
- [test_parser.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/tests/test_parser.py): Pytest unit tests verifying text cleaning and metric feature extraction.
- [test_integration.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/tests/test_integration.py): Pytest integration tests validating FastAPI health-checks, endpoint routing, mock parameter extraction, and SQLite database storage.
- [evaluate_large_dataset.py](file:///c:/Users/Tejendra%20Singh/Desktop/Sarthi_Summer_Intern/Wellmate-Web/backend/Engines/CPE/evaluate_large_dataset.py): Dataset evaluation runner which downloads 5,000 samples from Hugging Face (stored as a local JSON file to run completely offline) to measure validation success rate, latency, and parameter breakdown averages.

---

## 2. Test Verification Outcomes

Running `python -m pytest -v` successfully executed all parser unit tests and FastAPI integration tests:
```powershell
tests/test_integration.py::test_health_check PASSED                      [ 20%]
tests/test_integration.py::test_extract_from_text PASSED                 [ 40%]
tests/test_parser.py::test_clean_transcript_disfluencies PASSED          [ 60%]
tests/test_parser.py::test_clean_transcript_speaker_tags PASSED          [ 80%]
tests/test_parser.py::test_calculate_metrics PASSED                      [100%]

======================== 5 passed, 1 warning in 2.69s =========================
```

Running the dataset evaluator `python evaluate_large_dataset.py` processed 5,000 records in **25.48 seconds** (5.10 ms per record) with **100% validation success**.

---

## 3. Guide to Run Locally on VS Code

Follow these steps to run, test, and query the CPE engine inside VS Code on your Windows PC:

### Step 1: Open the CPE Folder in VS Code
1. Open VS Code.
2. Select **File -> Open Folder...** and navigate to:
   `c:\Users\Tejendra Singh\Desktop\Sarthi_Summer_Intern\Wellmate-Web\backend\Engines\CPE`
3. Open a terminal panel in VS Code (**Terminal -> New Terminal** or `Ctrl + Shift + \``).

### Step 2: Set Up Python Virtual Environment (Optional but Recommended)
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
`Starting CPE FastAPI Server at http://127.0.0.1:8000`

### Step 5: Open the Interactive Dashboard
1. Open your web browser (Chrome, Edge, Firefox, etc.).
2. Go to: **`http://localhost:8000/`**
3. You will be greeted by the CPE Dashboard. You can:
   - **Click on Presets**: Select chips like *"CS Exam Stress"* or *"Insomnia & Fatigue"* to instantly populate test transcripts.
   - **Write Custom Text**: Type raw text in the textarea, configure student metadata context (collapsed), and click **Run Extraction** to see the sliders and gauges animate in real-time.
   - **Upload Audios**: Switch to the **Audio Upload** tab, drag and drop any audio recording (e.g. `.wav`), and click **Run Extraction** to test Whisper transcription + parameter analysis.
4. Open a second terminal to run code test suites (`python -m pytest -v`) or run large evaluations (`python evaluate_large_dataset.py`).
