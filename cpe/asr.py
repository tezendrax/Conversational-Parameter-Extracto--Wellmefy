import os
import time
import logging
from typing import Dict, Any, Tuple
from cpe.config import settings

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading on each request
_whisper_model = None

def get_whisper_model() -> Any:
    """
    Lazily initializes and returns the Whisper model.
    Attempts faster-whisper first, falls back to openai-whisper.
    """
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    model_size = settings.WHISPER_MODEL_SIZE
    device = settings.WHISPER_DEVICE
    compute_type = settings.WHISPER_COMPUTE_TYPE
    
    # On CPU, force float32 or int8, float16 is not supported on all CPUs
    if device == "cpu" and compute_type == "default":
        compute_type = "int8" if "faster_whisper" in globals() else "float32"

    logger.info(f"Loading Whisper model '{model_size}' on '{device}' with precision '{compute_type}'...")
    start_time = time.time()
    
    try:
        from faster_whisper import WhisperModel
        # Use CPU/GPU settings
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"Loaded faster-whisper model in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        logger.warning(f"Failed to load faster-whisper, falling back to openai-whisper. Error: {e}")
        try:
            import whisper
            _whisper_model = whisper.load_model(model_size, device=device)
            logger.info(f"Loaded openai-whisper model in {time.time() - start_time:.2f} seconds.")
        except Exception as e2:
            logger.error(f"Failed to load any Whisper implementation: {e2}")
            _whisper_model = None
            raise e2
            
    return _whisper_model

def transcribe_audio(audio_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Transcribes audio file to text and computes ASR features (e.g. pause density).
    Returns:
        Tuple of (transcribed_text, metrics_dict)
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found at: {audio_path}")
        
    model = get_whisper_model()
    
    # Check model implementation type
    is_faster_whisper = hasattr(model, "transcribe") and not hasattr(model, "decoder")
    
    transcribed_text = ""
    active_speech_duration = 0.0
    total_duration = 0.0
    
    if is_faster_whisper:
        # faster-whisper returns generator of segments and info
        segments, info = model.transcribe(audio_path, beam_size=5)
        total_duration = info.duration
        
        segment_list = []
        for segment in segments:
            segment_list.append(segment.text)
            active_speech_duration += (segment.end - segment.start)
        transcribed_text = " ".join(segment_list)
    else:
        # openai-whisper returns a dict
        result = model.transcribe(audio_path)
        transcribed_text = result.get("text", "")
        
        # Calculate active speech duration from segments
        segments = result.get("segments", [])
        if segments:
            active_speech_duration = sum(s.get("end", 0.0) - s.get("start", 0.0) for s in segments)
            # Find max duration
            total_duration = max(segments[-1].get("end", 0.0), active_speech_duration)
            
    # Calculate pause density
    pause_density = 0.0
    if total_duration > 0:
        silence_duration = total_duration - active_speech_duration
        pause_density = max(0.0, silence_duration / total_duration)
        
    metrics = {
        "duration_seconds": round(total_duration, 2),
        "active_speech_seconds": round(active_speech_duration, 2),
        "pause_density": round(pause_density, 3)
    }
    
    return transcribed_text.strip(), metrics
