from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    # Storage
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    max_file_size_mb: int = 50
    
    # Processing
    enable_ocr: bool = True
    default_output_format: str = "markdown"  # markdown, json, html, text
    
    # Redis (for job queue)
    redis_url: str = "redis://localhost:6379/0"
    
    # App
    debug: bool = True
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
