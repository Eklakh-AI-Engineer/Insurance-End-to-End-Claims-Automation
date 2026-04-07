"""
main.py — FastAPI application entry point.
"""
from __future__ import annotations
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routes.claims import router as claims_router
from .routes.admin import router as admin_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ── Create DB tables ──────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Upload directory ──────────────────────────────────────────────────────────
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="End-to-End Insurance Claims Automation System with AI-powered fraud detection and auto-settlement.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(claims_router)
app.include_router(admin_router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Insurance Claims Automation API",
        "docs": "/docs",
        "health": "/health",
    }
