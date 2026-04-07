"""
admin.py — Admin dashboard and claim management routes.
GET /admin/dashboard
GET /admin/claims
GET /admin/heatmap
"""
from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, ClaimStatus, User, FraudLog
from ..schemas import (
    DashboardStats, PaginatedClaims, ClaimListItem, FraudHeatmapResponse, HeatmapCell
)

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    """Aggregate statistics for the admin overview cards."""

    def count_by(status: ClaimStatus) -> int:
        return db.query(func.count(Claim.id)).filter(Claim.status == status).scalar() or 0

    total = db.query(func.count(Claim.id)).scalar() or 0
    approved = count_by(ClaimStatus.APPROVED)
    flagged = count_by(ClaimStatus.FLAGGED)
    pending = count_by(ClaimStatus.PENDING)
    rejected = count_by(ClaimStatus.REJECTED)

    total_payout = db.query(func.coalesce(func.sum(Claim.settled_amount), 0)).scalar() or 0.0
    avg_fraud = db.query(func.coalesce(func.avg(Claim.fraud_score), 0)).scalar() or 0.0
    avg_amount = db.query(func.coalesce(func.avg(Claim.requested_amount), 0)).scalar() or 0.0

    return DashboardStats(
        total_claims=total,
        approved=approved,
        flagged=flagged,
        pending=pending,
        rejected=rejected,
        total_payout=round(float(total_payout), 2),
        avg_fraud_score=round(float(avg_fraud), 4),
        avg_claim_amount=round(float(avg_amount), 2),
    )


@router.get("/claims", response_model=PaginatedClaims)
def list_claims(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Paginated list of claims with optional status filter."""
    q = (
        db.query(Claim, User)
        .outerjoin(User, Claim.user_id == User.id)
    )
    if status:
        try:
            q = q.filter(Claim.status == ClaimStatus(status))
        except ValueError:
            pass  # invalid status → return all

    total = q.count()
    offset = (page - 1) * page_size
    rows = q.order_by(Claim.submitted_at.desc()).offset(offset).limit(page_size).all()

    items = []
    for claim, user in rows:
        items.append(ClaimListItem(
            claim_id=claim.id,
            full_name=user.full_name if user else "Unknown",
            claim_type=claim.claim_type,
            requested_amount=claim.requested_amount,
            estimated_payout=claim.estimated_payout,
            fraud_score=claim.fraud_score,
            status=claim.status,
            submitted_at=claim.submitted_at,
        ))

    total_pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedClaims(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/heatmap", response_model=FraudHeatmapResponse)
def fraud_heatmap(db: Session = Depends(get_db)):
    """
    Returns average fraud score bucketed by claim_type × hour-of-day.
    Powers the heatmap visualisation on the admin dashboard.
    """
    rows = (
        db.query(
            Claim.claim_type,
            extract("hour", Claim.submitted_at).label("hour_bucket"),
            func.avg(Claim.fraud_score).label("avg_fraud"),
            func.count(Claim.id).label("cnt"),
        )
        .filter(Claim.fraud_score.isnot(None))
        .group_by(Claim.claim_type, "hour_bucket")
        .all()
    )

    cells = [
        HeatmapCell(
            claim_type=r.claim_type.value,
            hour_bucket=int(r.hour_bucket),
            avg_fraud_score=round(float(r.avg_fraud), 4),
            count=int(r.cnt),
        )
        for r in rows
    ]
    return FraudHeatmapResponse(cells=cells)
