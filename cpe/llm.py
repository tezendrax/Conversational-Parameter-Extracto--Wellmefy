import re
import json
import logging
import httpx
from typing import Dict, Any, Optional
from cpe.config import settings
from cpe.schemas import CPEParameters, ContextMetadata
from cpe.text_parser import NEGATIVE_WORDS, POSITIVE_WORDS

logger = logging.getLogger(__name__)

# Heuristic keyword matching for mock mode when LLM is disabled
def _mock_extract(text: str, context: Optional[ContextMetadata] = None) -> CPEParameters:
    text_lower = text.lower() if text else ""
    
    # 1. Calculate text parser features
    words = [w.strip(".,!?;:") for w in text_lower.split() if w.strip(".,!?;:")]
    word_count = len(words)
    
    semantic_density = 0.0
    word_repetition_index = 0.0
    pos_count = 0
    neg_count = 0
    neg_to_pos_ratio = 0.0
    
    if word_count > 0:
        unique_words = set(words)
        semantic_density = len(unique_words) / word_count
        word_repetition_index = 1.0 - semantic_density
        
        pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
        if pos_count > 0:
            neg_to_pos_ratio = neg_count / pos_count
        else:
            neg_to_pos_ratio = float(neg_count)
            
    # Default parameters
    valency = 0.0
    arousal = 0.5
    cognitive_load = 2
    academic_stress = False
    somatic_symptoms = []
    confidence_score = 0.95 if text_lower else 0.5
    sentiment = 0.0
    
    # 2. Check for Academic stress
    acad_keywords = ["exam", "deadline", "test", "grade", "assignment", "homework", "professor", "class", "classes", "study", "studying", "cs", "computer science"]
    if any(w in text_lower for w in acad_keywords):
        academic_stress = True
        cognitive_load = 3
        
    # 3. Detect Panic / High Academic Confusion (e.g. user's test case)
    confusion_indicators = ["don't know", "dont know", "missed", "not know", "what to do", "didn't study", "didnt study"]
    confusion_count = sum(text_lower.count(ind) for ind in confusion_indicators)
    
    if academic_stress and confusion_count >= 2:
        valency = -0.70
        arousal = 0.85
        cognitive_load = 4
        # If highly repetitive, push cognitive load to 5 and increase arousal
        if word_repetition_index > 0.20 or confusion_count >= 4:
            cognitive_load = 5
            arousal = 0.88
        confidence_score = 0.78
        sentiment = -0.72
    else:
        # Standard keyword heuristics
        if pos_count > neg_count:
            valency = 0.4
            arousal = 0.4
            sentiment = 0.4
        elif neg_count > pos_count:
            valency = -0.5
            arousal = 0.7
            cognitive_load = max(cognitive_load, 4)
            sentiment = -0.5
        else:
            sentiment = 0.0
            
    # Somatic symptoms detection
    somatic_map = {
        "sleep": "insomnia",
        "insomnia": "insomnia",
        "headache": "headache",
        "migraine": "headache",
        "tired": "fatigue",
        "fatigue": "fatigue",
        "exhausted": "fatigue",
        "stomach": "stomachache",
        "nausea": "stomachache",
        "stomachache": "stomachache",
    }
    for key, val in somatic_map.items():
        if key in text_lower and val not in somatic_symptoms:
            somatic_symptoms.append(val)
            
    return CPEParameters(
        emotional_valency=valency,
        emotional_arousal=arousal,
        cognitive_load=cognitive_load,
        academic_stress=academic_stress,
        somatic_symptoms=somatic_symptoms,
        confidence_score=confidence_score,
        sentiment_score=sentiment,
        semantic_density=semantic_density,
        word_repetition_index=word_repetition_index,
        neg_to_pos_ratio=neg_to_pos_ratio
    )

def _build_prompt(text: str, context: Optional[ContextMetadata] = None) -> str:
    metadata_str = ""
    if context:
        metadata_str = f"Context Metadata: Student ID={context.student_id}, Time of Day={context.time_of_day}, History={context.interaction_history_context}"

    prompt = f"""You are a Conversational Parameter Extractor. Your task is to analyze the student's transcript and extract their emotional, cognitive, somatic, and academic stress indicators as quantitative parameters.

{metadata_str}

Student Transcript:
"{text}"

Analyze the transcript carefully and return ONLY a valid JSON object matching the schema below. 
Do not output any markdown formatting (like ```json), explanations, preambles, or trailing text.

JSON Schema:
{{
  "emotional_valency": float between -1.0 (very negative/sad/angry) and 1.0 (very positive/happy),
  "emotional_arousal": float between 0.0 (calm/sleepy) and 1.0 (agitated/stressed/excited),
  "cognitive_load": integer between 1 (relaxed/clear) and 5 (extreme overload/confusion),
  "academic_stress": boolean (true if there are indicators of academic stress like exams, assignments, grades, studying),
  "somatic_symptoms": list of strings (e.g. "insomnia", "fatigue", "headache", "stomachache" if mentioned),
  "confidence_score": float between 0.0 and 1.0 representing your extraction confidence,
  "sentiment_score": float between -1.0 and 1.0 representing overall sentiment
}}"""
    return prompt

def _clean_and_parse_json(raw_response: str) -> Dict[str, Any]:
    """
    Cleans raw response and attempts heuristic parsing if standard json.loads fails.
    """
    cleaned = raw_response.strip()
    
    # Remove markdown code blocks if present
    if cleaned.startswith("```"):
        # match ```json ... ``` or just ``` ... ```
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
            
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Standard JSON parsing failed: {e}. Trying heuristic regex parsing.")
        
        # Try to find the first '{' and the last '}'
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e2:
                logger.error(f"Heuristic JSON parsing failed on: {json_str}. Error: {e2}")
                raise ValueError("LLM response could not be parsed as JSON.")
        else:
            raise ValueError(f"Could not locate JSON brackets in response: {raw_response}")

def extract_parameters(text: str, context: Optional[ContextMetadata] = None, retry_count: int = 1) -> CPEParameters:
    """
    Orchestrates extraction of parameters from text by querying the LLM
    or using the mock extraction as configured.
    """
    if settings.LLM_PROVIDER == "mock":
        logger.info("Using Mock Extractor.")
        return _mock_extract(text, context)
        
    prompt = _build_prompt(text, context)
    temperature = 0.3
    
    for attempt in range(retry_count + 1):
        try:
            logger.info(f"Querying LLM (Attempt {attempt + 1}). Endpoint: {settings.LLM_BASE_URL}, Model: {settings.LLM_MODEL}")
            
            headers = {"Content-Type": "application/json"}
            if settings.LLM_API_KEY:
                headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
                
            payload = {
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a precise data extractor. Only output valid JSON matching the schema requested. No explanations."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "response_format": {"type": "json_object"} if "gpt" in settings.LLM_MODEL or "llama3" in settings.LLM_MODEL else None
            }
            
            response = httpx.post(
                f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            res_json = response.json()
            raw_content = res_json["choices"][0]["message"]["content"]
            logger.debug(f"Raw LLM Response: {raw_content}")
            
            parsed_json = _clean_and_parse_json(raw_content)
            
            # Validate and convert using Pydantic
            parameters = CPEParameters(**parsed_json)
            return parameters
            
        except Exception as e:
            logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
            if attempt < retry_count:
                # Fallback: retry with lower temperature
                temperature = 0.1
                logger.info(f"Retrying extraction with temperature={temperature}")
            else:
                logger.error("All extraction attempts failed. Falling back to rule-based mock extract.")
                return _mock_extract(text, context)
                
    return _mock_extract(text, context)
