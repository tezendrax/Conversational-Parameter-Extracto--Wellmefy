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

def test_custom_heuristics():
    # 1. Test context-aware academic stress negation
    payload_negation = {
        "text": "My classes are going fine, and I'm not particularly worried about academics.",
        "context": {
            "student_id": "student_neg",
            "time_of_day": "morning",
            "interaction_history_context": "None"
        }
    }
    response_neg = client.post("/api/v1/cpe/extract", json=payload_negation)
    assert response_neg.status_code == 200
    params_neg = response_neg.json()["parameters"]
    assert params_neg["academic_stress"] is False

    # 2. Test somatic symptom extraction and normalization
    payload_somatic = {
        "text": "My heartbeat is racing and I feel nauseous. Also my appetite has decreased.",
        "context": {
            "student_id": "student_somatic",
            "time_of_day": "afternoon",
            "interaction_history_context": "None"
        }
    }
    response_som = client.post("/api/v1/cpe/extract", json=payload_somatic)
    assert response_som.status_code == 200
    params_som = response_som.json()["parameters"]
    assert "racing heartbeat" in params_som["somatic_symptoms"]
    assert "nausea" in params_som["somatic_symptoms"]
    assert "reduced appetite" in params_som["somatic_symptoms"]

    # 3. Test mixed-emotion reasoning (pride + interview anxiety)
    payload_mixed = {
        "text": "I'm proud of my project, but I'm worried about internship interviews.",
        "context": {
            "student_id": "student_mixed",
            "time_of_day": "evening",
            "interaction_history_context": "None"
        }
    }
    response_mix = client.post("/api/v1/cpe/extract", json=payload_mixed)
    assert response_mix.status_code == 200
    params_mix = response_mix.json()["parameters"]
    assert 0.20 <= params_mix["emotional_valency"] <= 0.30
    assert 0.15 <= params_mix["sentiment_score"] <= 0.25

def test_somatic_explicit_vs_inferred_and_causal_stress():
    # 1. Test "My classes are going well. I'm worried about my grandfather."
    # Expect: academic_stress = False, valency is negative (-0.45), explicit_symptoms = empty []
    payload_causal = {
        "text": "My classes are going well. I'm worried about my grandfather.",
        "context": {
            "student_id": "student_causal_test",
            "time_of_day": "morning",
            "interaction_history_context": "None"
        }
    }
    response_causal = client.post("/api/v1/cpe/extract", json=payload_causal)
    assert response_causal.status_code == 200
    params_causal = response_causal.json()["parameters"]
    assert params_causal["academic_stress"] is False
    assert params_causal["emotional_valency"] == -0.45
    assert params_causal["explicit_symptoms"] == []
    
    # 2. Test "I got no sleep last night because I was studying all night for 20 hours."
    # Expect: inferred_risks contains "sleep deprivation risk", explicit_symptoms does not contain "insomnia"
    payload_inferred = {
        "text": "I got no sleep last night because I was studying all night for 20 hours.",
        "context": {
            "student_id": "student_inferred_test",
            "time_of_day": "night",
            "interaction_history_context": "None"
        }
    }
    response_inf = client.post("/api/v1/cpe/extract", json=payload_inferred)
    assert response_inf.status_code == 200
    params_inf = response_inf.json()["parameters"]
    assert "sleep deprivation risk" in params_inf["inferred_risks"]
    assert "insomnia" not in params_inf["explicit_symptoms"]
