import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

# Ensure test environment config is active
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///cpe_large_evaluation.sqlite"

from cpe.config import settings
from cpe.schemas import ContextMetadata
from cpe.text_parser import clean_transcript, calculate_metrics
from cpe.llm import extract_parameters
from cpe.db import init_db, save_extraction

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OFFLINE_FILE_PATH = "data/emotion_5k_offline.json"

def download_dataset_offline(num_samples: int = 5000) -> List[Dict[str, Any]]:
    """
    Downloads the dataset from Hugging Face if not present, and saves it locally.
    Loads it from the local JSON file if already downloaded.
    """
    os.makedirs("data", exist_ok=True)
    
    if os.path.exists(OFFLINE_FILE_PATH):
        logger.info(f"Loading dataset offline from: {OFFLINE_FILE_PATH}")
        with open(OFFLINE_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
            
    logger.info(f"Offline dataset not found. Downloading {num_samples} samples from Hugging Face...")
    from datasets import load_dataset
    dataset = load_dataset("dair-ai/emotion", split="train")
    samples = dataset.select(range(min(num_samples, len(dataset))))
    
    items = []
    for i, item in enumerate(samples):
        items.append({
            "id": f"student_eval_{i+1:04d}",
            "text": item["text"],
            "hf_label": int(item["label"])  # HF label (0: sadness, 1: joy, 2: love, 3: anger, 4: fear, 5: surprise)
        })
        
    logger.info(f"Saving dataset locally to: {OFFLINE_FILE_PATH}")
    with open(OFFLINE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        
    return items

def run_large_scale_evaluation():
    init_db()
    items = download_dataset_offline(5000)
    total_count = len(items)
    
    logger.info(f"Starting evaluation of {total_count} records...")
    
    start_time = time.time()
    success_count = 0
    results = []
    
    # Track statistics
    valencies = []
    arousals = []
    cognitive_loads = []
    academic_stress_count = 0
    somatic_symptoms_count = 0
    somatic_types = {}
    
    for idx, item in enumerate(items):
        text = item["text"]
        student_id = item["id"]
        
        # Log progress periodically
        if (idx + 1) % 1000 == 0 or idx == 0:
            logger.info(f"Processing progress: {idx + 1}/{total_count} ({(idx + 1)/total_count*100:.1f}%)")
            
        try:
            # 1. Clean
            cleaned = clean_transcript(text)
            
            # 2. Metrics
            metrics = calculate_metrics(cleaned)
            
            # 3. Extract Parameters
            context = ContextMetadata(student_id=student_id)
            params = extract_parameters(cleaned, context)
            
            # 4. Validate Schema constraints
            valency_ok = -1.0 <= params.emotional_valency <= 1.0
            arousal_ok = 0.0 <= params.emotional_arousal <= 1.0
            cognitive_ok = 1 <= params.cognitive_load <= 5
            confidence_ok = 0.0 <= params.confidence_score <= 1.0
            
            is_valid = valency_ok and arousal_ok and cognitive_ok and confidence_ok
            if is_valid:
                success_count += 1
                
            # Aggregate stats
            valencies.append(params.emotional_valency)
            arousals.append(params.emotional_arousal)
            cognitive_loads.append(params.cognitive_load)
            if params.academic_stress:
                academic_stress_count += 1
            if params.somatic_symptoms:
                somatic_symptoms_count += 1
                for sym in params.somatic_symptoms:
                    somatic_types[sym] = somatic_types.get(sym, 0) + 1
                    
            # Save to temporary DB
            save_extraction(
                student_id=student_id,
                text=cleaned,
                parameters=params,
                pause_density=None,
                semantic_density=metrics["semantic_density"],
                neg_to_pos_ratio=metrics["linguistic_markers"]["neg_to_pos_ratio"]
            )
            
        except Exception as e:
            logger.error(f"Error processing item {student_id}: {e}")
            
    end_time = time.time()
    total_time = end_time - start_time
    avg_latency = (total_time / total_count) * 1000
    
    success_rate = (success_count / total_count) * 100
    
    avg_valency = sum(valencies) / len(valencies) if valencies else 0
    avg_arousal = sum(arousals) / len(arousals) if arousals else 0
    avg_cog_load = sum(cognitive_loads) / len(cognitive_loads) if cognitive_loads else 0
    academic_stress_pct = (academic_stress_count / total_count) * 100
    somatic_symptoms_pct = (somatic_symptoms_count / total_count) * 100
    
    print("\n" + "="*80)
    print("LARGE SCALE EVALUATION SUMMARY")
    print("="*80)
    print(f"Total Datasets Processed:          {total_count}")
    print(f"JSON Validation Success Rate:      {success_rate:.2f}%")
    print(f"Total Processing Time:             {total_time:.2f} seconds")
    print(f"Average Latency Per Record:        {avg_latency:.2f} ms")
    print(f"Average Emotional Valency (Pos):   {avg_valency:.4f}")
    print(f"Average Emotional Arousal (Energy):{avg_arousal:.4f}")
    print(f"Average Cognitive Load Index:      {avg_cog_load:.2f} / 5")
    print(f"Academic Stress Indicator Rate:    {academic_stress_pct:.2f}%")
    print(f"Somatic Symptoms Detected Rate:    {somatic_symptoms_pct:.2f}%")
    if somatic_types:
        print(f"Somatic Complaint Breakdowns:      {somatic_types}")
    print("="*80 + "\n")
    
    # Save Report
    with open("cpe_large_evaluation_report.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_datasets_processed": total_count,
            "json_validation_success_rate": success_rate,
            "total_processing_time_seconds": total_time,
            "avg_latency_ms": avg_latency,
            "average_emotional_valency": avg_valency,
            "average_emotional_arousal": avg_arousal,
            "average_cognitive_load": avg_cog_load,
            "academic_stress_percentage": academic_stress_pct,
            "somatic_symptoms_percentage": somatic_symptoms_pct,
            "somatic_complaint_breakdown": somatic_types
        }, f, indent=2)

if __name__ == "__main__":
    run_large_scale_evaluation()
