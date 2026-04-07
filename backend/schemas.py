"""
schemas.py — Pydantic request/response models.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from .models import ClaimStatus, ClaimType


# ── Claim Submission ──────────────────────────────────────────────────────────

class ClaimSubmitRequest(BaseModel):
    """Sent as form-data alongside file upload(s)."""
    claim_type: ClaimType
    description: str = Field(..., min_length=20, max_length=5000)
    requested_amount: float = Field(..., gt=0)
    incident_date: Optional[datetime] = None
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    policy_number: Optional[str] = None


class AIScores(BaseModel):
    fraud_score: float
    anomaly_score: float
    image_valid: bool
    estimated_payout: float
    payout_match_pct: float


class ClaimResponse(BaseModel):
    claim_id: UUID
    status: ClaimStatus
    decision_reason: str
    ai_scores: AIScores
    settled_amount: Optional[float] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


# ── Fraud Check ───────────────────────────────────────────────────────────────

class FraudCheckRequest(BaseModel):
    claim_id: UUID


class FraudCheckResponse(BaseModel):
    claim_id: UUID
    fraud_score: float
    anomaly_score: float
    flagged_rules: List[str]
    feature_breakdown: Dict[str, float]


# ── Admin Dashboard ───────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_claims: int
    approved: int
    flagged: int
    pending: int
    rejected: int
    total_payout: float
    avg_fraud_score: float
    avg_claim_amount: float


class ClaimListItem(BaseModel):
    claim_id: UUID
    full_name: str
    claim_type: ClaimType
    requested_amount: float
    estimated_payout: Optional[float]
    fraud_score: Optional[float]
    status: ClaimStatus
    submitted_at: datetime

    class Config:
        from_attributes = True


class PaginatedClaims(BaseModel):
    items: List[ClaimListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Fraud Heatmap ─────────────────────────────────────────────────────────────

class HeatmapCell(BaseModel):
    claim_type: str
    hour_bucket: int          # 0-23
    avg_fraud_score: float
    count: int


class FraudHeatmapResponse(BaseModel):
    cells: List[HeatmapCell]
