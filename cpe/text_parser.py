import re
from typing import Dict, Any, Tuple

# Common disfluencies to remove, optionally consuming surrounding commas and spaces
DISFLUENCIES = [
    r",?\s*\b(um+s?|uh+s?)\b\s*,?",
    r",?\s*\b(er+s?|ah+s?)\b\s*,?",
    r",?\s*\b(like)\b\s*,?",
    r",?\s*\b(so)\b\s*,?",
    r",?\s*\b(you\s+know)\b\s*,?",
    r",?\s*\b(i\s+mean)\b\s*,?"
]

# Simple emotion lexicon for linguistic markers
POSITIVE_WORDS = {
    "happy", "good", "great", "excellent", "fine", "okay", "excited", "hopeful",
    "calm", "relaxed", "peaceful", "better", "improving", "success", "succeed",
    "love", "glad", "joy", "cheerful", "confident", "healthy", "sleep", "rested"
}

NEGATIVE_WORDS = {
    "sad", "bad", "terrible", "worst", "stressed", "overwhelmed", "anxious", "worry",
    "worried", "fail", "failed", "failure", "hate", "angry", "mad", "depressed",
    "insomnia", "tired", "exhausted", "fatigue", "pain", "hurt", "lonely", "alone",
    "cry", "crying", "scared", "fear", "panic", "difficult", "hard", "struggle", "hopeless",
    "don't", "dont", "didn't", "didnt", "not", "no", "cant", "can't", "missed", "miss", "lost", "confused", "nervous"
}

def clean_transcript(text: str) -> str:
    """
    Cleans transcript text by:
    1. Converting to lowercase
    2. Removing disfluencies (um, uh, like, etc.)
    3. Fixing spacing and punctuation
    4. Removing speaker tags (e.g. 'Student: ', 'Speaker 1: ')
    """
    if not text:
        return ""
    
    # 1. Remove speaker tags (e.g., 'Student:', 'Speaker 1:', '[Therapist]:')
    # Match strings ending in a colon optionally enclosed in brackets at start or after a newline
    cleaned = re.sub(r'(?i)(?:^|\n)\s*(?:\[?[a-z0-9\s_-]+\]?\s*:\s*)', ' ', text)
    
    # Convert to lowercase
    cleaned = cleaned.lower()
    
    # Replace newlines with spaces
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ')
    
    # 2. Remove disfluencies
    for pattern in DISFLUENCIES:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    
    # 3. Clean up multiple spaces and punctuation artifacts
    cleaned = re.sub(r'(,\s*)+,', ',', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Clean up spaces around punctuation (e.g. "hello , world" -> "hello, world")
    cleaned = re.sub(r'\s+([.,!?;:])', r'\1', cleaned)
    
    # Strip leading/trailing commas or spaces
    cleaned = re.sub(r'^[,\s]+', '', cleaned)
    cleaned = re.sub(r'[,\s]+$', '', cleaned)
    
    return cleaned

def calculate_metrics(text: str) -> Dict[str, Any]:
    """
    Calculates feature engineering metrics from the transcript:
    - Semantic Density: unique vocabulary to word count ratio (high repetition reduces density)
    - Word Repetition Index: ratio of repeating words (1.0 - semantic_density)
    - Linguistic Markers: ratio of negative words to positive words
    - Word Count: total words
    """
    words = [w.strip(".,!?;:") for w in text.lower().split() if w.strip(".,!?;:")]
    word_count = len(words)
    
    if not words:
        return {
            "semantic_density": 0.0,
            "word_repetition_index": 0.0,
            "linguistic_markers": {
                "positive_count": 0,
                "negative_count": 0,
                "neg_to_pos_ratio": 0.0
            },
            "word_count": 0
        }
        
    unique_words = set(words)
    # Semantic Density = unique vocabulary / total words (high repetition reduces density)
    semantic_density = len(unique_words) / word_count
    word_repetition_index = 1.0 - semantic_density
    
    # Linguistic markers (positive / negative word count)
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    
    neg_to_pos_ratio = 0.0
    if pos_count > 0:
        neg_to_pos_ratio = neg_count / pos_count
    else:
        neg_to_pos_ratio = float(neg_count)  # If pos_count is 0, ratio equals neg_count
        
    return {
        "semantic_density": round(semantic_density, 3),
        "word_repetition_index": round(word_repetition_index, 3),
        "linguistic_markers": {
            "positive_count": pos_count,
            "negative_count": neg_count,
            "neg_to_pos_ratio": round(neg_to_pos_ratio, 3)
        },
        "word_count": word_count
    }
