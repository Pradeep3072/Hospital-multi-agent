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
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Security
    SECRET_KEY: str = "dev-secret-hospital-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # RAG
    TOP_K_RETRIEVAL: int = 4
    USE_BM25_HYBRID: bool = True

    # Notifications
    NOTIFICATION_CHANNEL: str = "mock"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
