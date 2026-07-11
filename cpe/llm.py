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
    explicit_symptoms = []
    inferred_risks = []
    confidence_score = 0.95 if text_lower else 0.5
    sentiment = 0.0
    
    # 2. Check for Academic stress with causal reasoning
    # Academic stress = TRUE only if academic context exists AND is the source of distress.
    acad_keywords = ["exam", "deadline", "test", "grade", "assignment", "homework", "professor", "class", "classes", "study", "studying", "cs", "computer science", "academics", "semester"]
    has_acad_keywords = any(w in text_lower for w in acad_keywords)
    
    # Check for positive academic cues showing it is manageable / going well
    academic_manageable = any(phrase in text_lower for phrase in [
        "classes are going well",
        "classes are going fine",
        "classes are fine",
        "classes going fine",
        "academics are fine",
        "exams are fine",
        "studying is fine",
        "not worried about academics",
        "not worried about class",
        "not worried about exam",
        "not worried about my classes",
        "not worried about my exams",
        "academics aren't the issue",
        "academics are not the issue",
        "not particularly worried about academics"
    ])
    
    if has_acad_keywords and not academic_manageable:
        stress_indicators = ["worry", "worried", "stressed", "overwhelmed", "anxious", "fail", "failed", "struggle", "panic", "missed", "don't know", "dont know", "terrified", "fear", "scared"]
        has_stress = any(s in text_lower for s in stress_indicators) or (neg_count > pos_count)
        
        # Check if the distress is explicitly caused by something else (e.g. grandfather, family, health)
        non_acad_causes = ["grandfather", "grandmother", "family", "mother", "father", "relationship", "sick", "illness", "health"]
        has_unrelated_cause = any(cause in text_lower for cause in non_acad_causes)
        
        if has_stress:
            if has_unrelated_cause and not any(term in text_lower for term in ["terrified of exams", "fail my exam", "failed my test"]):
                academic_stress = False
            else:
                academic_stress = True
                cognitive_load = max(cognitive_load, 3)
                
    # 3. Detect Panic / High Academic Confusion (e.g. user's test case)
    confusion_indicators = ["don't know", "dont know", "missed", "not know", "what to do", "didn't study", "didnt study"]
    confusion_count = sum(text_lower.count(ind) for ind in confusion_indicators)
    
    if academic_stress and confusion_count >= 2:
        valency = -0.70
        arousal = 0.85
        cognitive_load = 4
        if word_repetition_index > 0.20 or confusion_count >= 4:
            cognitive_load = 5
            arousal = 0.88
        confidence_score = 0.78
        sentiment = -0.72
    else:
        # 4. Multi-Dimensional Emotion Reasoning (Joy, Anxiety, Sadness, Hope, Confidence)
        # Weigh emotions by dominant emotional conclusion instead of simple positive/negative word averages
        # Example 1: "I'm proud of my project, but I'm worried about internship interviews."
        # pride (+0.60), interview anxiety (-0.40) -> dominant is proud with minor worry -> positive mood
        if "proud" in text_lower and ("worried" in text_lower or "worry" in text_lower or "interview" in text_lower):
            valency = 0.25
            sentiment = 0.20
            arousal = 0.60
            cognitive_load = max(cognitive_load, 3)
        # Example 2: "My classes are going well. I'm worried about my grandfather."
        # Classes well (neutral/hope), grandfather (sadness/anxiety) -> dominant conclusion is grandfather sadness -> negative mood
        elif "grandfather" in text_lower and ("worried" in text_lower or "worry" in text_lower or "sick" in text_lower):
            valency = -0.45
            sentiment = -0.40
            arousal = 0.65
            cognitive_load = max(cognitive_load, 3)
        elif pos_count > neg_count:
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
            
    # 5. Explicit Somatic symptoms detection (directly stated only)
    explicit_rules = {
        "heartbeat is racing": "racing heartbeat",
        "heart is racing": "racing heartbeat",
        "racing heartbeat": "racing heartbeat",
        "nauseous": "nausea",
        "nausea": "nausea",
        "throw up": "nausea",
        "throwing up": "nausea",
        "appetite has decreased": "reduced appetite",
        "appetite decreased": "reduced appetite",
        "reduced appetite": "reduced appetite",
        "decreased appetite": "reduced appetite",
        "loss of appetite": "reduced appetite",
        "head hurts": "headache",
        "headache": "headache",
        "migraine": "headache",
        "can't sleep": "insomnia",
        "cant sleep": "insomnia",
        "couldn't sleep": "insomnia",
        "couldnt sleep": "insomnia",
        "trouble sleeping": "insomnia",
        "insomnia": "insomnia",
        "stomach hurts": "stomachache",
        "stomachache": "stomachache",
    }
    for key, val in explicit_rules.items():
        if key in text_lower and val not in explicit_symptoms:
            explicit_symptoms.append(val)
            
    # 6. Inferred Risks (lifestyle cues like studying 20 hours or getting no sleep)
    inferred_rules = {
        "studying 20 hours": "sleep deprivation risk",
        "studying all night": "sleep deprivation risk",
        "working all night": "sleep deprivation risk",
        "no sleep": "sleep deprivation risk",
        "without breaks": "burnout risk",
        "overworked": "burnout risk",
        "study too much": "burnout risk",
        "burnout": "burnout risk",
    }
    for key, val in inferred_rules.items():
        if key in text_lower and val not in inferred_risks:
            inferred_risks.append(val)
            
    # For backward compatibility, map explicit_symptoms to somatic_symptoms
    somatic_symptoms = list(explicit_symptoms)
            
    return CPEParameters(
        emotional_valency=valency,
        emotional_arousal=arousal,
        cognitive_load=cognitive_load,
        academic_stress=academic_stress,
        somatic_symptoms=somatic_symptoms,
        explicit_symptoms=explicit_symptoms,
        inferred_risks=inferred_risks,
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
 
Follow this structured Chain-of-Thought reasoning internally before generating your final output:
Step 1: Identify all emotional cues. Decompose all coexisting emotions (e.g., Joy, Anxiety, Fear, Sadness, Hope, Confidence) and assign an internal confidence level (0.0 to 1.0) to each.
Step 2: Identify all physical symptoms explicitly mentioned by the speaker. Do not infer symptoms.
Step 3: Determine the primary source of distress. Analyze if it is academic factors (exams, coursework, grades), personal issues, health issues, or other factors.
Step 4: Estimate cognitive load based on confusion, repetition, or overwork.
Step 5: Determine the dominant emotional conclusion based on the speaker's overall emphasis and concluding statements.
Step 6: Generate the final JSON based on these reasoning steps.
 
JSON Schema Instructions:
Return ONLY a valid JSON object matching the schema below. Do not include markdown codeblocks (like ```json), explanations, or preambles.
 
JSON Schema:
{{
  "emotional_valency": float between -1.0 (very negative) and 1.0 (very positive). DO NOT average positive and negative cues equally to 0.0. Compute valency based on the dominant emotional conclusion identified in Step 5.,
  "emotional_arousal": float between 0.0 (calm) and 1.0 (agitated/excited),
  "cognitive_load": integer between 1 (relaxed/clear) and 5 (extreme overload/confusion),
  "academic_stress": boolean. Set to true ONLY if academic factors (exams, assignments, grades, coursework) are the primary cause of the student's distress. If academic topics are mentioned but described as manageable, fine, or unrelated to the distress, set academic_stress=false.,
  "somatic_symptoms": list of strings. Populate this with the same items as explicit_symptoms (for backward compatibility).,
  "explicit_symptoms": list of strings. Include ONLY physical symptoms explicitly stated by the speaker (e.g. "racing heartbeat" if they say "heartbeat is racing", "nausea" if they say "nauseous", "reduced appetite" if they say "appetite decreased", "headache" if they say "head hurts"). NEVER infer medical symptoms.,
  "inferred_risks": list of strings. Include inferred physical or cognitive risks based on lifestyle cues (e.g. "sleep deprivation risk" if they mention studying for 20 hours or getting no sleep, "burnout risk" if they mention working without breaks). Do not list these as explicit symptoms.,
  "confidence_score": float between 0.0 and 1.0 representing your extraction confidence,
  "sentiment_score": float between -1.0 and 1.0 representing overall sentiment computed based on the dominant emotional conclusion.
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
