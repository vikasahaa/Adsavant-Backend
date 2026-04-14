"""
Application configuration using Pydantic Settings.
All config is loaded from environment variables or .env file.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — loaded from env vars or .env file."""

    # Application
    APP_NAME: str = "AdSavant API"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8501",  # Streamlit default
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://localhost:63342"
    ]

    # ML Model
    MODEL_PATH: str = str(Path(__file__).parent.parent / "ml" / "adsavant_model_v3.pkl")

    # Engagement thresholds (must match training config)
    ER_HIGH_THRESHOLD: float = 5.0
    ER_AVG_THRESHOLD: float = 2.0

    # Image processing
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # CLIP config (must match training)
    CLIP_MODEL: str = "ViT-B-32"
    CLIP_PRETRAINED: str = "laion2b_s34b_b79k"
    N_AUGMENT_VIEWS: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
