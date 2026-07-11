# Conversational Parameter Extractor (CPE)

The Conversational Parameter Extractor (CPE) transforms raw natural language (speech or text) into a structured numerical vector representing emotional, cognitive, and somatic markers. By utilizing LLM-based parsing and deterministic validation, it bridges the gap between conversational therapy interactions and quantitative digital twin state modeling.

---

## 🚀 Features

*   **Speech-to-Text (ASR)**: Powered by Whisper to transcribe audio files and calculate **Pause Density** (silence ratio).
*   **Text Cleaning & Normalization**: Cleans conversational fillers ("um", "uh", "like", "you know"), strips speaker tags (e.g. `Student:`), and calculates **Semantic Density** and **Word Repetition Index**.
*   **LLM Parameter Extraction**: Analyzes transcripts using LLaMA-3-8B-Instruct (via OpenAI-compatible API or offline mock simulator) to extract valency, arousal, cognitive load, academic stress, and somatic symptoms.
*   **Pydantic Validation**: Strict conformity guards ensuring JSON schema and boundary validity with automated low-temperature retry logic.
*   **Privacy Cache**: SQLite database caching with a 24-hour retention policy that automatically wipes raw transcripts to protect student privacy.
*   **Glassmorphic Testing Dashboard**: A premium frontend web dashboard to test text and audio extractions in real-time.

---

## 🛠️ API Endpoints

### 1. Extract from Text
*   **Method**: `POST`
*   **Path**: `/api/v1/cpe/extract`
*   **Payload**:
    ```json
    {
      "text": "I feel so overwhelmed by my programming exam tomorrow, I could not sleep last night.",
      "context": {
        "student_id": "student_123",
        "time_of_day": "evening",
        "interaction_history_context": "Exam anxiety history."
      }
    }
    ```

### 2. Extract from Audio
*   **Method**: `POST`
*   **Path**: `/api/v1/cpe/extract/audio`
*   **Content-Type**: `multipart/form-data`
*   **Payload Fields**: `file` (audio file), `student_id`, `time_of_day`, `interaction_history_context`

### 3. Health Status
*   **Method**: `GET`
*   **Path**: `/health`

---

## 💻 Local Running Guide

### Step 1: Install Dependencies
Ensure you have Python 3.10+ installed. Run:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Configure Environment (`.env`)
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Default mode is `LLM_PROVIDER=mock`, which runs offline without requiring API keys.

### Step 3: Run the Server
```bash
python run_server.py
```
Open **`http://localhost:8000/`** in your browser to view the interactive web dashboard!

---

## 🧪 Testing & Evaluation

### Run Unit/Integration Tests
```bash
python -m pytest -v
```

### Run Large-Scale Offline Evaluation
Processes 5,000 records from Hugging Face's `dair-ai/emotion` dataset, stores them locally, and generates a markdown report:
```bash
python evaluate_large_dataset.py
```

---

## 🌐 Deployment

*   **Frontend Dashboard**: Hosted on **Vercel** via `vercel.json` static rewrites.
*   **Backend Hosting**: Packaged as a containerized app via the included `Dockerfile` (installs FFmpeg and pre-caches Whisper weights). Easily deployable on **Hugging Face Spaces**, **Render**, or **Railway**.
