import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    CPE_HOST: str = "127.0.0.1"
    CPE_PORT: int = 8000
    
    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "default"
    
    LLM_PROVIDER: str = "mock"  # "mock" or "openai_compatible"
    LLM_MODEL: str = "llama3-8b"
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: Optional[str] = "mock-key"
    
    DATABASE_URL: str = "sqlite:///cpe_database.sqlite"
    CACHE_DURATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
