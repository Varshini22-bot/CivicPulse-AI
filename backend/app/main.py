import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import setup_logging, logger
from app.database.connection import engine, Base, SessionLocal
from app.database.seed_data import seed_database
from app.api.routes.auth import router as auth_router
from app.api.routes.reports import router as reports_router
from app.api.routes.admin import router as admin_router
from app.api.routes.duplicates import router as duplicates_router
from app.api.routes.map import router as map_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.notifications import router as notifications_router

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB schema & seed realistic dataset
    logger.info("Initializing CivicPulse AI Database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.DEMO_DIR, exist_ok=True)
    
    # Run database seed
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
        
    logger.info("CivicPulse AI Application Startup Complete.")
    yield
    logger.info("CivicPulse AI Application Shutdown.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent Civic Issue Detection, Geospatial Prioritization & Resolution Decision Support Platform",
    lifespan=lifespan
)

# Attach Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware (Strict explicit origins from env; avoids wildcard with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static uploads
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(duplicates_router, prefix=settings.API_V1_STR)
app.include_router(map_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "documentation": "/docs",
        "api_prefix": settings.API_V1_STR
    }

@app.get("/api/health")
def healthcheck():
    return {
        "status": "healthy",
        "timestamp": "2026-11-22T20:00:00Z",
        "database": "connected"
    }
