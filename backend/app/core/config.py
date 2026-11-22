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
    DUPLICATE_RADIUS_METERS: float = 100.0  # Default fallback radius
    DUPLICATE_CATEGORY_RADII: dict = {
        "pothole": 25.0,                 # Localized road crater
        "road_damage": 35.0,             # Longitudinal cracking
        "garbage_overflow": 30.0,        # Waste bin location
        "illegal_dumping": 40.0,         # Uncontained debris pile
        "water_leakage": 75.0,           # Pipe segment leak
        "blocked_drain": 60.0,           # Silted drain segment
        "broken_streetlight": 80.0,      # Continuous streetlight fixture
        "damaged_infrastructure": 40.0   # Sidewalk/railing defect
    }
    DUPLICATE_TIME_WINDOW_DAYS: int = 30     # Within 30 days
    DUPLICATE_SCORE_THRESHOLD: float = 0.65  # 65% composite match

    # Geospatial DBSCAN Clustering Parameters (Configured from k-distance elbow analysis)
    DBSCAN_EPS_METERS: float = 300.0  # 300m neighborhood radius
    DBSCAN_MIN_SAMPLES: int = 3
    
    # Civic Hub Coordinates (Default: Bengaluru Center)
    DEFAULT_LAT: float = 12.9716
    DEFAULT_LNG: float = 77.5946

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}

settings = Settings()
