import math
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()

# Configure engine
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Custom spatial Haversine distance function registered in SQLite
def sqlite_haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lng pairs on Earth."""
    if any(v is None for v in (lat1, lon1, lat2, lon2)):
        return None
    try:
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        delta_phi = math.radians(float(lat2) - float(lat1))
        delta_lambda = math.radians(float(lon2) - float(lon1))
        
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c
    except Exception:
        return None

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        # Register haversine_distance(lat1, lon1, lat2, lon2) -> distance in meters
        dbapi_connection.create_function("haversine_meters", 4, sqlite_haversine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
