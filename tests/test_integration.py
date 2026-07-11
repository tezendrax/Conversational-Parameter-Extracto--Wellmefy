import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment variables before importing app
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///test_cpe_database.sqlite"

from cpe.main import app
from cpe.db import Base, engine, SessionLocal, CPEExtractionModel

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    # Create test database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up database tables and drop test database file
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_cpe_database.sqlite"):
        try:
            os.remove("test_cpe_database.sqlite")
        except Exception:
            pass

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_extract_from_text():
    payload = {
        "text": "I, um, feel so overwhelmed by my computer science exam tomorrow, I couldn't sleep.",
        "context": {
            "student_id": "student_test_123",
            "time_of_day": "night",
            "interaction_history_context": "Struggling with CS"
        }
    }
    
    response = client.post("/api/v1/cpe/extract", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "transcript" in data
    # Check cleaned transcript contains no disfluencies "um" or "so"
    assert "um" not in data["transcript"]
    assert "so" not in data["transcript"]
    assert "overwhelmed" in data["transcript"]
    
    params = data["parameters"]
    assert "emotional_valency" in params
    assert "emotional_arousal" in params
    assert "cognitive_load" in params
    assert params["academic_stress"] is True
    assert "insomnia" in params["somatic_symptoms"]
    
    # Check that database has recorded the extraction
    db = SessionLocal()
    try:
        record = db.query(CPEExtractionModel).filter_by(student_id="student_test_123").first()
        assert record is not None
        assert record.academic_stress is True
        assert "insomnia" in record.somatic_symptoms
        assert record.transcribed_text == data["transcript"]
    finally:
        db.close()
