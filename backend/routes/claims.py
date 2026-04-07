"""
claims.py — Routes for claim submission and fraud checking.
POST /submit-claim
POST /check-fraud
"""
from __future__ import annotations
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Claim, ClaimStatus, ClaimType, FraudLog, User
from ..schemas import (
    ClaimResponse, AIScores, FraudCheckRequest, FraudCheckResponse,
)
from ..services.ocr_service import extract_document_data
from ..services.fraud_service import run_fraud_check
from ..services.image_service import analyse_images
from ..services.payout_service import estimate_payout

router = APIRouter(prefix="/api", tags=["Claims"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _save_uploads(files: List[UploadFile], claim_id: str) -> List[str]:
    """Persist uploaded files to disk; return list of saved paths."""
    upload_dir = Path(settings.upload_dir) / claim_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        if f.filename:
            dest = upload_dir / f.filename
            with open(dest, "wb") as out:
                shutil.copyfileobj(f.file, out)
            paths.append(str(dest))
    return paths


def _get_or_create_user(db: Session, email: str, full_name: str, phone: str, policy_number: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            policy_number=policy_number,
        )
        db.add(user)
        db.flush()
    return user


def _determine_claim_days(db: Session, user_id) -> int:
    """Days since user's most recent prior claim (default 365 if first claim)."""
    last = (
        db.query(Claim)
        .filter(Claim.user_id == user_id)
        .order_by(Claim.submitted_at.desc())
        .first()
    )
    if last is None:
        return 365
    delta = datetime.now(timezone.utc) - last.submitted_at.replace(tzinfo=timezone.utc)
    return max(delta.days, 0)


@router.post("/submit-claim", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def submit_claim(
    claim_type: str = Form(...),
    description: str = Form(...),
    requested_amount: float = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    policy_number: str = Form(""),
    incident_date: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """
    Full AI pipeline:
    1. Save uploads
    2. OCR / LLM extraction
    3. Fraud check (XGBoost + Isolation Forest)
    4. Image analysis (ResNet + ELA)
    5. Payout estimation
    6. Auto-settlement decision
    """
    # ── Validate claim type ───────────────────────────────────────────────────
    try:
        c_type = ClaimType(claim_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid claim_type: {claim_type}")

    # ── Persist user ──────────────────────────────────────────────────────────
    user = _get_or_create_user(db, email, full_name, phone, policy_number)
    days_since = _determine_claim_days(db, user.id)

    # ── Save files ────────────────────────────────────────────────────────────
    temp_id = str(uuid.uuid4())
    saved_paths = _save_uploads(files, temp_id)

    # ── Step 1: OCR / LLM extraction ─────────────────────────────────────────
    logger.info(f"[{temp_id}] Running OCR extraction on {len(saved_paths)} file(s)")
    extracted = extract_document_data(saved_paths)

    # ── Step 2: Fraud check ───────────────────────────────────────────────────
    logger.info(f"[{temp_id}] Running fraud check")
    fraud_result = run_fraud_check(
        claim_type=claim_type,
        requested_amount=requested_amount,
        history_claim_count=user.history_claim_count,
        days_since_last_claim=days_since,
        description=description,
        image_count=len(saved_paths),
        extracted_data=extracted,
    )
    fraud_score = fraud_result["hybrid_score"]
    anomaly_score = fraud_result["anomaly_score"]

    # ── Step 3: Image analysis ────────────────────────────────────────────────
    logger.info(f"[{temp_id}] Analysing images")
    image_result = analyse_images(saved_paths)
    image_valid = image_result["image_valid"]

    # Boost fraud score if forgery is suspected
    if image_result["forgery_suspected"]:
        fraud_score = min(fraud_score + 0.25, 1.0)
        fraud_result["flagged_rules"].append("IMAGE_FORGERY: ELA detected possible manipulation")

    # ── Step 4: Payout estimation ─────────────────────────────────────────────
    logger.info(f"[{temp_id}] Estimating payout")
    payout_result = estimate_payout(
        claim_type=claim_type,
        requested_amount=requested_amount,
        history_claim_count=user.history_claim_count,
        days_since_last_claim=days_since,
        fraud_score=fraud_score,
    )
    estimated_payout = payout_result["estimated_payout"]
    payout_match = payout_result["payout_match_pct"]

    # ── Step 5: Auto-settlement decision ─────────────────────────────────────
    if fraud_score < settings.fraud_threshold and payout_match >= settings.payout_match_threshold and image_valid:
        decision = ClaimStatus.APPROVED
        settled_amount = estimated_payout
        reason = (
            f"✅ Auto-approved. Fraud score {fraud_score:.3f} < {settings.fraud_threshold}, "
            f"payout match {payout_match:.1%} ≥ {settings.payout_match_threshold:.0%}, "
            f"image valid."
        )
    else:
        decision = ClaimStatus.FLAGGED
        settled_amount = None
        reasons = []
        if fraud_score >= settings.fraud_threshold:
            reasons.append(f"fraud score {fraud_score:.3f} ≥ threshold {settings.fraud_threshold}")
        if payout_match < settings.payout_match_threshold:
            reasons.append(f"payout match {payout_match:.1%} < {settings.payout_match_threshold:.0%}")
        if not image_valid:
            reasons.append("image analysis found insufficient damage evidence")
        reason = "🔴 Flagged for manual review: " + "; ".join(reasons)

    # ── Persist claim ─────────────────────────────────────────────────────────
    incident_dt = None
    if incident_date:
        try:
            incident_dt = datetime.fromisoformat(incident_date)
        except ValueError:
            pass

    claim = Claim(
        user_id=user.id,
        claim_type=c_type,
        description=description,
        requested_amount=requested_amount,
        incident_date=incident_dt,
        image_paths=saved_paths,
        extracted_data=extracted,
        fraud_score=fraud_result["fraud_score"],
        anomaly_score=anomaly_score,
        image_valid=image_valid,
        estimated_payout=estimated_payout,
        payout_match_pct=payout_match,
        status=decision,
        decision_reason=reason,
        settled_amount=settled_amount,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(claim)

    # ── Persist fraud log ─────────────────────────────────────────────────────
    fraud_log = FraudLog(
        claim_id=claim.id,
        fraud_score=fraud_score,
        anomaly_score=anomaly_score,
        feature_breakdown=fraud_result["feature_breakdown"],
        flagged_rules=fraud_result["flagged_rules"],
    )
    db.add(fraud_log)

    # ── Update user claim count ───────────────────────────────────────────────
    user.history_claim_count += 1
    db.commit()
    db.refresh(claim)

    logger.info(f"[{claim.id}] Decision: {decision.value}")

    return ClaimResponse(
        claim_id=claim.id,
        status=decision,
        decision_reason=reason,
        ai_scores=AIScores(
            fraud_score=fraud_result["fraud_score"],
            anomaly_score=anomaly_score,
            image_valid=image_valid,
            estimated_payout=estimated_payout,
            payout_match_pct=payout_match,
        ),
        settled_amount=settled_amount,
        submitted_at=claim.submitted_at,
    )


@router.post("/check-fraud", response_model=FraudCheckResponse)
async def check_fraud(payload: FraudCheckRequest, db: Session = Depends(get_db)):
    """Re-run fraud analysis on an existing claim (e.g. after manual review)."""
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    user = db.query(User).filter(User.id == claim.user_id).first()
    history = user.history_claim_count if user else 0

    fraud_result = run_fraud_check(
        claim_type=claim.claim_type.value,
        requested_amount=claim.requested_amount,
        history_claim_count=history,
        days_since_last_claim=365,
        description=claim.description,
        image_count=len(claim.image_paths or []),
        extracted_data=claim.extracted_data,
    )

    return FraudCheckResponse(
        claim_id=claim.id,
        fraud_score=fraud_result["fraud_score"],
        anomaly_score=fraud_result["anomaly_score"],
        flagged_rules=fraud_result["flagged_rules"],
        feature_breakdown=fraud_result["feature_breakdown"],
    )
