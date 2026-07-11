import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from cpe.config import settings
from cpe.schemas import ExtractionRequest, ContextMetadata
from cpe.text_parser import clean_transcript, calculate_metrics
from cpe.llm import extract_parameters

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Fallback synthetic student dialogues for local offline testing
SYNTHETIC_DATASET = [
    {
        "text": "I am feeling so overwhelmed by my computer science exam tomorrow, I couldn't sleep.",
        "student_id": "student_01",
        "expected_academic_stress": True,
        "expected_somatic": "insomnia"
    },
    {
        "text": "I feel great! I finally finished my project early and I'm going to hang out with my friends.",
        "student_id": "student_02",
        "expected_academic_stress": False,
        "expected_somatic": None
    },
    {
        "text": "I'm so tired, my head hurts and I can't seem to focus on anything. There's too much homework.",
        "student_id": "student_03",
        "expected_academic_stress": True,
        "expected_somatic": "headache"
    },
    {
        "text": "I have been having stomachaches all day because of the presentations we have to do in class.",
        "student_id": "student_04",
        "expected_academic_stress": True,
        "expected_somatic": "stomachache"
    },
    {
        "text": "I'm doing okay, just a normal day. Studying for my math quiz later.",
        "student_id": "student_05",
        "expected_academic_stress": True,
        "expected_somatic": None
    }
]

def load_evaluation_dataset() -> List[Dict[str, Any]]:
    """
    Attempts to load a sample dataset from Hugging Face.
    Falls back to synthetic student dataset if offline or slow.
    """
    logger.info("Attempting to load evaluation dataset...")
    try:
        from datasets import load_dataset
        # Load a small slice of dair-ai/emotion
        logger.info("Downloading sample from Hugging Face 'dair-ai/emotion' dataset...")
        dataset = load_dataset("dair-ai/emotion", split="train")
        samples = dataset.select(range(5))
        
        evaluation_items = []
        for i, item in enumerate(samples):
            evaluation_items.append({
                "text": item["text"],
                "student_id": f"hf_student_{i+1}",
                "expected_academic_stress": None,
                "expected_somatic": None
            })
        logger.info(f"Successfully loaded {len(evaluation_items)} samples from Hugging Face.")
        return evaluation_items
    except Exception as e:
        logger.warning(f"Could not load Hugging Face dataset ({e}). Falling back to synthetic student dialogues.")
        return SYNTHETIC_DATASET

def run_evaluation():
    items = load_evaluation_dataset()
    results = []
    
    success_count = 0
    total_count = len(items)
    
    print("\n" + "="*80)
    print("RUNNING CPE DATASET EVALUATION")
    print(f"Provider: {settings.LLM_PROVIDER} | Model: {settings.LLM_MODEL}")
    print("="*80 + "\n")
    
    for idx, item in enumerate(items):
        text = item["text"]
        student_id = item["student_id"]
        
        print(f"[{idx+1}/{total_count}] Processing Student ID: {student_id}")
        print(f"  Input text: \"{text}\"")
        
        try:
            # 1. Clean Text
            cleaned_text = clean_transcript(text)
            
            # 2. Extract metrics
            metrics = calculate_metrics(cleaned_text)
            
            # 3. Parameter extraction
            context = ContextMetadata(student_id=student_id, time_of_day="afternoon")
            params = extract_parameters(cleaned_text, context)
            
            # 4. Verification & Validation
            # Verify constraints
            valency_ok = -1.0 <= params.emotional_valency <= 1.0
            arousal_ok = 0.0 <= params.emotional_arousal <= 1.0
            cognitive_ok = 1 <= params.cognitive_load <= 5
            confidence_ok = 0.0 <= params.confidence_score <= 1.0
            
            is_valid = valency_ok and arousal_ok and cognitive_ok and confidence_ok
            if is_valid:
                success_count += 1
                
            results.append({
                "student_id": student_id,
                "raw_text": text,
                "cleaned_text": cleaned_text,
                "metrics": metrics,
                "parameters": params.model_dump(),
                "is_valid": is_valid
            })
            
            print(f"  Cleaned text: \"{cleaned_text}\"")
            print(f"  Extracted Parameters:")
            print(f"    - Emotional Valency: {params.emotional_valency:.2f}")
            print(f"    - Emotional Arousal: {params.emotional_arousal:.2f}")
            print(f"    - Cognitive Load: {params.cognitive_load}")
            print(f"    - Academic Stress: {params.academic_stress}")
            print(f"    - Somatic Symptoms: {params.somatic_symptoms}")
            print(f"    - Confidence Score: {params.confidence_score:.2f}")
            print(f"    - Sentiment Score: {params.sentiment_score:.2f}")
            print(f"  Text Metrics: Density={metrics['semantic_density']:.2f}, Neg/Pos Ratio={metrics['linguistic_markers']['neg_to_pos_ratio']:.2f}")
            print(f"  Validation status: {'PASSED' if is_valid else 'FAILED'}")
            print("-" * 50)
            
        except Exception as e:
            logger.error(f"Failed to process sample {student_id}: {e}")
            results.append({
                "student_id": student_id,
                "raw_text": text,
                "error": str(e),
                "is_valid": False
            })
            print(f"  [ERROR] Failed to process sample: {e}")
            print("-" * 50)
            
    success_rate = (success_count / total_count) * 100
    
    # Save Report
    report_path = "evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# CPE Evaluation Report\n\n")
        f.write(f"- **Timestamp**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **LLM Provider**: {settings.LLM_PROVIDER}\n")
        f.write(f"- **LLM Model**: {settings.LLM_MODEL}\n")
        f.write(f"- **Total Samples Evaluated**: {total_count}\n")
        f.write(f"- **JSON Schema Validation Success Rate**: {success_rate:.2f}%\n\n")
        
        f.write("## Evaluation Table\n\n")
        f.write("| Student ID | Cleaned Transcript | Valency | Arousal | Cog Load | Academic Stress | Somatic Symptoms | Status |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        
        for r in results:
            if "error" in r:
                f.write(f"| {r['student_id']} | `{r['raw_text']}` | N/A | N/A | N/A | N/A | N/A | `ERROR` |\n")
            else:
                p = r["parameters"]
                status_str = "✅ PASSED" if r["is_valid"] else "❌ FAILED"
                somatic_str = ", ".join(p['somatic_symptoms']) if p['somatic_symptoms'] else "None"
                f.write(f"| {r['student_id']} | {r['cleaned_text']} | {p['emotional_valency']:.2f} | {p['emotional_arousal']:.2f} | {p['cognitive_load']} | {p['academic_stress']} | {somatic_str} | {status_str} |\n")
                
        f.write("\n## Summary Metrics\n\n")
        valid_params = [r["parameters"] for r in results if "parameters" in r]
        if valid_params:
            avg_valency = sum(p["emotional_valency"] for p in valid_params) / len(valid_params)
            avg_arousal = sum(p["emotional_arousal"] for p in valid_params) / len(valid_params)
            avg_cog_load = sum(p["cognitive_load"] for p in valid_params) / len(valid_params)
            academic_stress_percentage = (sum(1 for p in valid_params if p["academic_stress"]) / len(valid_params)) * 100
            
            f.write(f"- **Average Emotional Valency**: {avg_valency:.3f}\n")
            f.write(f"- **Average Emotional Arousal**: {avg_arousal:.3f}\n")
            f.write(f"- **Average Cognitive Load Index**: {avg_cog_load:.2f}/5\n")
            f.write(f"- **Academic Stress Indicator Rate**: {academic_stress_percentage:.1f}%\n")
            
    print(f"\nEvaluation Complete. Success Rate: {success_rate:.2f}%")
    print(f"Results written to: {report_path}\n")

if __name__ == "__main__":
    run_evaluation()
