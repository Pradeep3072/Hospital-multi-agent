import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hospital Multi-Agent AI System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./hospital.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Gemini LLM
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Security
    SECRET_KEY: str = "dev-secret-hospital-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # RAG
    TOP_K_RETRIEVAL: int = 4
    USE_BM25_HYBRID: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

# Ensure GOOGLE_API_KEY is available in os.environ for Google ADK and GenAI
if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
    os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]


_gemini_client = None


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None and settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            print(f"Notice: Gemini client init error: {e}")
            _gemini_client = None
    return _gemini_client

