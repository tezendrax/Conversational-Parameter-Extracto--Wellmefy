import os
import time
import shutil
import tempfile
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from cpe.config import settings
from cpe.schemas import ExtractionRequest, APIResponse, ContextMetadata, CPEParameters
from cpe.text_parser import clean_transcript, calculate_metrics
from cpe.asr import transcribe_audio
from cpe.llm import extract_parameters
from cpe.db import init_db, save_extraction, purge_old_transcripts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up CPE Engine...")
    init_db()
    # Purge old transcripts on startup
    try:
        purged = purge_old_transcripts(settings.CACHE_DURATION_HOURS)
        if purged > 0:
            logger.info(f"Purged {purged} old transcript cache on startup.")
    except Exception as e:
        logger.error(f"Startup transcript purge failed: {e}")
    yield
    # Shutdown actions
    logger.info("Shutting down CPE Engine...")

app = FastAPI(
    title="Conversational Parameter Extractor (CPE)",
    description="Transforms raw speech/text into structured emotional, cognitive, and somatic markers.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "whisper_model": settings.WHISPER_MODEL_SIZE
    }

@app.post("/api/v1/cpe/extract", response_model=APIResponse)
async def extract_from_text(request: ExtractionRequest, background_tasks: BackgroundTasks):
    """
    Extracts student markers from a raw text transcript payload.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text transcript cannot be empty.")
        
    try:
        # 1. Clean transcript
        cleaned_text = clean_transcript(request.text)
        
        # 2. Extract metrics
        metrics = calculate_metrics(cleaned_text)
        
        # 3. Query LLM to extract parameters
        parameters = extract_parameters(cleaned_text, request.context)
        
        # Populate text metrics for response
        parameters.semantic_density = metrics["semantic_density"]
        parameters.word_repetition_index = metrics["word_repetition_index"]
        parameters.neg_to_pos_ratio = metrics["linguistic_markers"]["neg_to_pos_ratio"]
        
        # 4. Save to database
        background_tasks.add_task(
            save_extraction,
            student_id=request.context.student_id,
            text=cleaned_text,
            parameters=parameters,
            pause_density=None,
            semantic_density=metrics["semantic_density"],
            neg_to_pos_ratio=metrics["linguistic_markers"]["neg_to_pos_ratio"]
        )
        
        # Schedule cache cleaning
        background_tasks.add_task(purge_old_transcripts, settings.CACHE_DURATION_HOURS)
        
        return APIResponse(
            transcript=cleaned_text,
            parameters=parameters
        )
    except Exception as e:
        logger.error(f"Text parameter extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cpe/extract/audio", response_model=APIResponse)
async def extract_from_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    student_id: str = Form("unknown"),
    time_of_day: Optional[str] = Form(None),
    interaction_history_context: Optional[str] = Form(None)
):
    """
    Transcribes audio using Whisper ASR and extracts markers.
    """
    context = ContextMetadata(
        student_id=student_id,
        time_of_day=time_of_day,
        interaction_history_context=interaction_history_context
    )
    
    # 1. Save uploaded file to temp file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"cpe_{int(time.time())}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Received audio file {file.filename}, saved to temporary path {temp_path}")
        
        # 2. Transcribe audio with Whisper
        raw_transcript, asr_metrics = transcribe_audio(temp_path)
        
        # 3. Clean transcript
        cleaned_text = clean_transcript(raw_transcript)
        
        # 4. Calculate metrics
        metrics = calculate_metrics(cleaned_text)
        
        # 5. Extract parameters using LLM
        parameters = extract_parameters(cleaned_text, context)
        
        # Populate text metrics for response
        parameters.semantic_density = metrics["semantic_density"]
        parameters.word_repetition_index = metrics["word_repetition_index"]
        parameters.neg_to_pos_ratio = metrics["linguistic_markers"]["neg_to_pos_ratio"]
        
        # 6. Save results to DB
        background_tasks.add_task(
            save_extraction,
            student_id=student_id,
            text=cleaned_text,
            parameters=parameters,
            pause_density=asr_metrics["pause_density"],
            semantic_density=metrics["semantic_density"],
            neg_to_pos_ratio=metrics["linguistic_markers"]["neg_to_pos_ratio"]
        )
        
        # Schedule cache cleaning
        background_tasks.add_task(purge_old_transcripts, settings.CACHE_DURATION_HOURS)
        
        return APIResponse(
            transcript=cleaned_text,
            parameters=parameters
        )
        
    except FileNotFoundError as e:
        logger.error(f"ASR file not found: {e}")
        raise HTTPException(status_code=404, detail="Uploaded file could not be processed.")
    except Exception as e:
        logger.error(f"Audio parameter extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Temporary file {temp_path} deleted.")
            except Exception as ex:
                logger.warning(f"Failed to delete temp file {temp_path}: {ex}")

@app.post("/api/v1/cpe/purge")
def trigger_purge():
    """
    Manually triggers transcript cache purging.
    """
    try:
        count = purge_old_transcripts(settings.CACHE_DURATION_HOURS)
        return {"status": "success", "purged_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend static dashboard
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

