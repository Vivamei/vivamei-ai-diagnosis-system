"""
app/main.py

FastAPI application factory.
Assembles routers, middleware, and static files.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from core.config import get_settings
from core.logging import setup_logging

# Initialize logging
setup_logging()

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for static file serving
upload_dir = Path(__file__).resolve().parent.parent / "uploads"
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Register routers
app.include_router(health_router)
app.include_router(analysis_router)
