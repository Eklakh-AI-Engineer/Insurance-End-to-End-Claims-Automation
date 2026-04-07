"""
config.py — Centralised settings via Pydantic BaseSettings.
All values are read from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Insurance Claims Automation API"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/insurance_db"

    # ── AI / LLM ─────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "openai"          # "openai" | "gemini"

    # ── Upload ────────────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    # ── ML Model Paths ────────────────────────────────────────────────────────
    fraud_model_path: str = "../ml/models/fraud_xgb.pkl"
    iso_forest_path: str = "../ml/models/iso_forest.pkl"
    payout_model_path: str = "../ml/models/payout_model.pkl"

    # ── Auto-Settlement Thresholds ────────────────────────────────────────────
    fraud_threshold: float = 0.2          # below → safe
    payout_match_threshold: float = 0.90  # above → auto-approve

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
