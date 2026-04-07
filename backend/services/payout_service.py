"""
payout_service.py — Payout estimation + match percentage calculation.
Uses a trained GradientBoostingRegressor; falls back to a heuristic table.
"""
from __future__ import annotations
import logging
import pickle
from pathlib import Path

import numpy as np

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_payout_model = None

# Heuristic base rates per claim type (as a fraction of requested amount)
_BASE_RATES = {
    "health":   0.82,
    "auto":     0.74,
    "property": 0.68,
    "life":     0.90,
    "travel":   0.65,
}

CLAIM_TYPE_MAP = {"health": 0, "auto": 1, "property": 2, "life": 3, "travel": 4}


def _load_payout_model():
    global _payout_model
    if _payout_model is None:
        path = Path(__file__).parent.parent.parent / settings.payout_model_path.lstrip("../")
        if path.exists():
            with open(path, "rb") as f:
                _payout_model = pickle.load(f)
            logger.info("Payout model loaded.")
        else:
            logger.warning(f"Payout model not found at {path}. Using heuristic.")
    return _payout_model


def estimate_payout(
    claim_type: str,
    requested_amount: float,
    history_claim_count: int = 0,
    days_since_last_claim: int = 365,
    fraud_score: float = 0.0,
) -> dict:
    """
    Returns:
        {
            "estimated_payout": float,
            "payout_match_pct": float,  # 0-1 (similarity to requested)
            "recommendation":   str,
        }
    """
    model = _load_payout_model()

    if model is not None:
        features = np.array([[
            CLAIM_TYPE_MAP.get(claim_type, 0),
            requested_amount,
            history_claim_count,
            days_since_last_claim,
            fraud_score,
        ]])
        estimated = float(model.predict(features)[0])
    else:
        # Heuristic fallback
        rate = _BASE_RATES.get(claim_type, 0.70)
        # Penalise for high fraud score or frequent claims
        penalty = fraud_score * 0.3 + (0.05 if history_claim_count >= 3 else 0)
        estimated = requested_amount * max(rate - penalty, 0.10)

    # Clamp: payout can't exceed requested amount
    estimated = min(estimated, requested_amount)
    estimated = max(estimated, 0.0)

    # Match percentage: how close is request to our estimate?
    if requested_amount > 0:
        ratio = estimated / requested_amount
        # Convert to a directional match score (1.0 = perfect match)
        payout_match = float(np.clip(1 - abs(1 - ratio), 0, 1))
    else:
        payout_match = 0.0

    if payout_match >= 0.90:
        recommendation = "AMOUNT_VALID: Requested amount aligns with historical payouts."
    elif payout_match >= 0.70:
        recommendation = "AMOUNT_ADJUSTED: Payout slightly below request; flagged for review."
    else:
        recommendation = "AMOUNT_MISMATCH: Significant discrepancy — manual review required."

    return {
        "estimated_payout": round(estimated, 2),
        "payout_match_pct": round(payout_match, 4),
        "recommendation": recommendation,
    }
