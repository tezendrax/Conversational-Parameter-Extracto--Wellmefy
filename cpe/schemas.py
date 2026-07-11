from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class ContextMetadata(BaseModel):
    student_id: str = Field(default="unknown", description="Unique identifier for the student")
    time_of_day: Optional[str] = Field(default=None, description="Time of day context (e.g., morning, night)")
    interaction_history_context: Optional[str] = Field(default=None, description="Recent interaction context or summary")

class CPEParameters(BaseModel):
    emotional_valency: float = Field(
        ..., 
        description="Value representing emotional positivity or negativity, from -1.0 (very negative) to 1.0 (very positive)",
        ge=-1.0, 
        le=1.0
    )
    emotional_arousal: float = Field(
        ..., 
        description="Value representing emotional energy or activation level, from 0.0 (calm/sleepy) to 1.0 (highly excited/agitated)",
        ge=0.0, 
        le=1.0
    )
    cognitive_load: int = Field(
        ..., 
        description="Index representing mental effort or load, from 1 (low load) to 5 (extreme overload)",
        ge=1, 
        le=5
    )
    academic_stress: bool = Field(
        ..., 
        description="True if academic indicators of stress are present in input (exams, assignments, grades, deadlines)"
    )
    somatic_symptoms: List[str] = Field(
        default_factory=list, 
        description="List of somatic complaints identified (e.g., insomnia, fatigue, headache, stomachache)"
    )
    confidence_score: float = Field(
        default=1.0, 
        description="LLM evaluation confidence score, from 0.0 to 1.0",
        ge=0.0, 
        le=1.0
    )
    sentiment_score: float = Field(
        default=0.0,
        description="Overall sentiment score, from -1.0 to 1.0",
        ge=-1.0,
        le=1.0
    )
    semantic_density: float = Field(
        default=0.0,
        description="Density of unique words, from 0.0 to 1.0"
    )
    word_repetition_index: float = Field(
        default=0.0,
        description="Ratio of repeating words, from 0.0 to 1.0"
    )
    neg_to_pos_ratio: float = Field(
        default=0.0,
        description="Ratio of negative words to positive words"
    )

    @field_validator("cognitive_load", mode="before")
    @classmethod
    def clamp_cognitive_load(cls, v):
        if isinstance(v, (int, float)):
            return max(1, min(5, int(v)))
        return v

    @field_validator("emotional_valency", "sentiment_score", mode="before")
    @classmethod
    def clamp_valency_and_sentiment(cls, v):
        if isinstance(v, (int, float)):
            return max(-1.0, min(1.0, float(v)))
        return v

    @field_validator("emotional_arousal", "confidence_score", mode="before")
    @classmethod
    def clamp_arousal_and_confidence(cls, v):
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


class ExtractionRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Raw text transcript if audio is not uploaded")
    context: Optional[ContextMetadata] = Field(default_factory=ContextMetadata, description="Student and session metadata")


class APIResponse(BaseModel):
    transcript: str = Field(..., description="The processed clean transcript text")
    parameters: CPEParameters = Field(..., description="The extracted quantitative parameters")
