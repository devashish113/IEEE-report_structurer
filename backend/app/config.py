"""
Configuration module for IEEE Report Restructurer.
Loads environment variables and provides settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Groq API Configuration
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    
    # File Upload Settings
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = [".docx", ".pdf"]
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    
    # Word Count Thresholds (IEEE Section Length Control)
    # Must match frontend green zone: 200–400 words
    min_section_words: int = 200  # Expand if below this
    max_section_words: int = 400  # Compress only if above this
    target_section_words: int = 300  # Target words per major section
    
    # LLM Settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    max_concurrent_llm_calls: int = 5
    
    # Server Settings
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
