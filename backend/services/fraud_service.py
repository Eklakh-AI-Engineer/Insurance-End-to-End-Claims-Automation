"""
fraud_service.py — Hybrid fraud detection engine.
XGBoost (tabular patterns) + Isolation Forest (anomaly detection).
"""
from __future__ import annotations
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Lazy-loaded model singletons ──────────────────────────────────────────────
_xgb_model = None
_iso_model = None


def _load_model(path: str, label: str):
    resolved = Path(__file__).parent.parent.parent / path.lstrip("../")
    if not resolved.exists():
        logger.warning(f"{label} not found at {resolved}. Using heuristic fallback.")
        return None
    with open(resolved, "rb") as f:
        return pickle.load(f)


def _get_xgb():
    global _xgb_model
    if _xgb_model is None:
        _xgb_model = _load_model(settings.fraud_model_path, "XGBoost fraud model")
    return _xgb_model


def _get_iso():
    global _iso_model
    if _iso_model is None:
        _iso_model = _load_model(settings.iso_forest_path, "Isolation Forest")
    return _iso_model


# ── Feature Engineering ───────────────────────────────────────────────────────

CLAIM_TYPE_MAP = {"health": 0, "auto": 1, "property": 2, "life": 3, "travel": 4}


def build_feature_vector(
    claim_type: str,
    requested_amount: float,
    history_claim_count: int,
    days_since_last_claim: int,
    description_length: int,
    image_count: int,
    llm_confidence: float,
    llm_red_flag_count: int,
) -> np.ndarray:
    """Returns a 1-D numpy array in the exact order used during training."""
    return np.array([[
        CLAIM_TYPE_MAP.get(claim_type, 0),
        requested_amount,
        history_claim_count,
        days_since_last_claim,
        description_length,
        image_count,
        llm_confidence,
        llm_red_flag_count,
        requested_amount / max(history_claim_count + 1, 1),      # amount-per-claim ratio
        min(requested_amount / 10000, 10),                        # normalised amount cap
    ]])


FEATURE_NAMES = [
    "claim_type_enc",
    "requested_amount",
    "history_claim_count",
    "days_since_last_claim",
    "description_length",
    "image_count",
    "llm_confidence",
    "llm_red_flag_count",
    "amount_per_claim_ratio",
    "norm_amount",
]


# ── Rule-based flags ──────────────────────────────────────────────────────────

def _detect_rule_flags(
    requested_amount: float,
    history_claim_count: int,
    days_since_last_claim: int,
    llm_red_flag_count: int,
) -> list[str]:
    flags = []
    if requested_amount > 50_000:
        flags.append("HIGH_AMOUNT: Requested amount exceeds $50,000")
    if history_claim_count >= 3 and days_since_last_claim < 90:
        flags.append("FREQUENT_CLAIMS: 3+ claims within 90 days")
    if days_since_last_claim < 30:
        flags.append("RAPID_RECLAIM: Previous claim filed less than 30 days ago")
    if llm_red_flag_count > 0:
        flags.append(f"LLM_FLAGS: {llm_red_flag_count} suspicious element(s) detected in documents")
    return flags


# ── Heuristic fallback (no model) ─────────────────────────────────────────────

def _heuristic_fraud_score(features: np.ndarray) -> float:
    """Simple rule-based score when no ML model is available."""
    amount = features[0][1]
    history = features[0][2]
    days = features[0][3]
    score = 0.0
    if amount > 50_000:
        score += 0.35
    if amount > 100_000:
        score += 0.2
    if history >= 3 and days < 90:
        score += 0.25
    if days < 30:
        score += 0.15
    return min(score, 1.0)


# ── Main API ──────────────────────────────────────────────────────────────────

def run_fraud_check(
    claim_type: str,
    requested_amount: float,
    history_claim_count: int = 0,
    days_since_last_claim: int = 365,
    description: str = "",
    image_count: int = 1,
    extracted_data: Optional[dict] = None,
) -> dict:
    """
    Returns:
        {
            "fraud_score":   float [0,1],
            "anomaly_score": float [0,1],
            "hybrid_score":  float [0,1],   # weighted combination
            "flagged_rules": list[str],
            "feature_breakdown": dict,
        }
    """
    extracted = extracted_data or {}
    llm_confidence = extracted.get("confidence_score", 0.5)
    llm_red_flags = extracted.get("red_flags", [])

    features = build_feature_vector(
        claim_type=claim_type,
        requested_amount=requested_amount,
        history_claim_count=history_claim_count,
        days_since_last_claim=days_since_last_claim,
        description_length=len(description),
        image_count=image_count,
        llm_confidence=llm_confidence,
        llm_red_flag_count=len(llm_red_flags),
    )

    # ── XGBoost score ─────────────────────────────────────────────────────────
    xgb = _get_xgb()
    if xgb is not None:
        xgb_prob = float(xgb.predict_proba(features)[0][1])
    else:
        xgb_prob = _heuristic_fraud_score(features)

    # ── Isolation Forest score ────────────────────────────────────────────────
    iso = _get_iso()
    if iso is not None:
        # decision_function: more negative = more anomalous → normalise to [0,1]
        raw_iso = float(iso.decision_function(features)[0])
        # Typical range is roughly [-0.5, 0.5]; clamp & invert
        anomaly_score = float(np.clip(1 - (raw_iso + 0.5), 0, 1))
    else:
        anomaly_score = 0.0

    # ── Hybrid combination (60% XGBoost, 40% Isolation Forest) ───────────────
    hybrid_score = 0.6 * xgb_prob + 0.4 * anomaly_score

    # ── Rule flags ────────────────────────────────────────────────────────────
    flagged_rules = _detect_rule_flags(
        requested_amount, history_claim_count,
        days_since_last_claim, len(llm_red_flags),
    )
    if llm_red_flags:
        flagged_rules.extend([f"DOC_RED_FLAG: {f}" for f in llm_red_flags])

    # ── Feature breakdown for audit ───────────────────────────────────────────
    feature_breakdown = {
        name: float(features[0][i]) for i, name in enumerate(FEATURE_NAMES)
    }

    return {
        "fraud_score": round(xgb_prob, 4),
        "anomaly_score": round(anomaly_score, 4),
        "hybrid_score": round(hybrid_score, 4),
        "flagged_rules": flagged_rules,
        "feature_breakdown": feature_breakdown,
    }
