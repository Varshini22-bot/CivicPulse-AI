import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CivicPulse AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "civicpulse-secure-jwt-secret-key-32chars-min!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Defaults to SQLite with spatial functions; can be overridden to PostgreSQL+PostGIS
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./civicpulse.db")
    
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    DEMO_DIR: str = os.getenv("DEMO_DIR", "uploads/demo")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # Priority Scoring Engine Weights
    WEIGHT_SEVERITY: float = 0.35
    WEIGHT_SAFETY: float = 0.25
    WEIGHT_LOCATION_RISK: float = 0.15
    WEIGHT_COMMUNITY_IMPACT: float = 0.15
    WEIGHT_AGE: float = 0.10
    
    # Duplicate Detection Parameters
    DUPLICATE_RADIUS_METERS: float = 100.0  # Within 100 meters
    DUPLICATE_TIME_WINDOW_DAYS: int = 30     # Within 30 days
    DUPLICATE_SCORE_THRESHOLD: float = 0.65  # 65% composite match
    
    # Civic Hub Coordinates (Default: Bengaluru Center)
    DEFAULT_LAT: float = 12.9716
    DEFAULT_LNG: float = 77.5946

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}

settings = Settings()
