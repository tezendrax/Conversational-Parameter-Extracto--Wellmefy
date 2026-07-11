from datetime import datetime, timezone
import json
import logging
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from cpe.config import settings
from cpe.schemas import CPEParameters

logger = logging.getLogger(__name__)

Base = declarative_base()

class CPEExtractionModel(Base):
    __tablename__ = "cpe_extractions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    
    # Text contents (stored locally, to be purged after CACHE_DURATION_HOURS)
    transcribed_text = Column(Text, nullable=True)
    
    # Extracted parameters
    emotional_valency = Column(Float, nullable=False)
    emotional_arousal = Column(Float, nullable=False)
    cognitive_load = Column(Integer, nullable=False)
    academic_stress = Column(Boolean, nullable=False)
    somatic_symptoms = Column(Text, nullable=False)  # Stored as JSON string
    confidence_score = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    
    # Feature engineering metrics
    pause_density = Column(Float, nullable=True)
    semantic_density = Column(Float, nullable=True)
    neg_to_pos_ratio = Column(Float, nullable=True)
    
    # Raw LLM JSON output for debugging/audit logs
    raw_json_output = Column(Text, nullable=True)

# Create database engine
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes tables in the database."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e

def save_extraction(
    student_id: str,
    text: str,
    parameters: CPEParameters,
    pause_density: Optional[float] = None,
    semantic_density: Optional[float] = None,
    neg_to_pos_ratio: Optional[float] = None,
    raw_json: Optional[str] = None
) -> CPEExtractionModel:
    """
    Saves an extraction payload and related metrics to the database.
    """
    session = SessionLocal()
    try:
        db_record = CPEExtractionModel(
            student_id=student_id,
            timestamp=datetime.now(timezone.utc),
            transcribed_text=text,
            emotional_valency=parameters.emotional_valency,
            emotional_arousal=parameters.emotional_arousal,
            cognitive_load=parameters.cognitive_load,
            academic_stress=parameters.academic_stress,
            somatic_symptoms=json.dumps(parameters.somatic_symptoms),
            confidence_score=parameters.confidence_score,
            sentiment_score=parameters.sentiment_score,
            pause_density=pause_density,
            semantic_density=semantic_density,
            neg_to_pos_ratio=neg_to_pos_ratio,
            raw_json_output=raw_json or json.dumps(parameters.model_dump())
        )
        session.add(db_record)
        session.commit()
        session.refresh(db_record)
        logger.info(f"Saved CPE extraction record for student: {student_id}")
        return db_record
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save extraction record: {e}")
        raise e
    finally:
        session.close()

def purge_old_transcripts(hours: int = 24) -> int:
    """
    Purges/anonmyizes raw transcript text for records older than `hours` hours to ensure privacy.
    Keeps the quantitative metrics intact, but wipes out `transcribed_text` and `raw_json_output`.
    """
    session = SessionLocal()
    try:
        # Calculate cut-off time
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        
        # Select records created before the cutoff that still have transcripts
        records = session.query(CPEExtractionModel).filter(
            CPEExtractionModel.timestamp < cutoff,
            (CPEExtractionModel.transcribed_text.isnot(None) | CPEExtractionModel.raw_json_output.isnot(None))
        ).all()
        
        count = len(records)
        for record in records:
            # Overwrite raw transcript and raw JSON text to ensure privacy
            record.transcribed_text = "[WIPED FOR PRIVACY]"
            record.raw_json_output = "[WIPED FOR PRIVACY]"
            
        session.commit()
        if count > 0:
            logger.info(f"Anonymized {count} old transcript records older than {hours} hours.")
        return count
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to purge old transcripts: {e}")
        raise e
    finally:
        session.close()
