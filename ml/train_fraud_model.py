"""
train_fraud_model.py
====================
Generates 5,000 synthetic insurance claims and trains:
  1. XGBoost binary classifier  → fraud_xgb.pkl
  2. Isolation Forest           → iso_forest.pkl

Run:  python ml/train_fraud_model.py
"""
from __future__ import annotations
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb

SEED = 42
N_SAMPLES = 5_000
MODEL_DIR = Path(__file__).parent / "models"
DATA_DIR  = Path(__file__).parent / "data"
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

np.random.seed(SEED)

# ── Feature map (must match fraud_service.py build_feature_vector) ─────────────
CLAIM_TYPE_MAP = {"health": 0, "auto": 1, "property": 2, "life": 3, "travel": 4}
FEATURE_NAMES  = [
    "claim_type_enc", "requested_amount", "history_claim_count",
    "days_since_last_claim", "description_length", "image_count",
    "llm_confidence", "llm_red_flag_count",
    "amount_per_claim_ratio", "norm_amount",
]


def generate_synthetic_data(n: int = N_SAMPLES) -> pd.DataFrame:
    claim_types = np.random.choice(list(CLAIM_TYPE_MAP.keys()), n)
    enc_types   = np.array([CLAIM_TYPE_MAP[c] for c in claim_types])

    # Legitimate claims
    amounts           = np.abs(np.random.lognormal(mean=9, sigma=1.2, size=n))  # ~$8k median
    history_count     = np.random.poisson(lam=1.5, size=n)
    days_last         = np.random.exponential(scale=200, size=n).astype(int) + 1
    desc_len          = np.random.randint(50, 2000, size=n)
    image_count       = np.random.randint(1, 6, size=n)
    llm_conf          = np.random.beta(8, 2, size=n)        # mostly high confidence
    llm_red_flags     = np.random.poisson(lam=0.3, size=n)

    # Build fraud labels via rule-based signal + noise
    fraud_prob = (
        0.30 * (amounts > 80_000).astype(float)
        + 0.25 * (history_count >= 3).astype(float)
        + 0.20 * (days_last < 60).astype(float)
        + 0.15 * (llm_red_flags > 1).astype(float)
        + 0.05 * np.random.random(n)               # noise
    )
    fraud_prob = np.clip(fraud_prob, 0, 1)
    labels = (fraud_prob > 0.45).astype(int)

    # Inject obvious fraud rows (~10 %)
    n_fraud = int(n * 0.10)
    idx = np.random.choice(n, n_fraud, replace=False)
    amounts[idx]       *= np.random.uniform(3, 10, n_fraud)   # inflated amounts
    history_count[idx] += np.random.randint(4, 10, n_fraud)
    days_last[idx]      = np.random.randint(1, 20, n_fraud)
    llm_red_flags[idx] += np.random.randint(2, 6, n_fraud)
    labels[idx]         = 1

    amount_ratio = amounts / np.maximum(history_count + 1, 1)
    norm_amount  = np.clip(amounts / 10_000, 0, 10)

    df = pd.DataFrame({
        "claim_type_enc":       enc_types,
        "requested_amount":     amounts,
        "history_claim_count":  history_count,
        "days_since_last_claim":days_last,
        "description_length":   desc_len,
        "image_count":          image_count,
        "llm_confidence":       llm_conf,
        "llm_red_flag_count":   llm_red_flags,
        "amount_per_claim_ratio": amount_ratio,
        "norm_amount":          norm_amount,
        "fraud_label":          labels,
    })
    return df


def train():
    print("=" * 60)
    print("  Insurance Fraud Detection — Model Training")
    print("=" * 60)

    df = generate_synthetic_data()
    df.to_csv(DATA_DIR / "synthetic_claims.csv", index=False)
    print(f"✓ Generated {len(df)} synthetic claims → data/synthetic_claims.csv")
    print(f"  Fraud rate: {df['fraud_label'].mean():.1%}")

    X = df[FEATURE_NAMES].values
    y = df["fraud_label"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)

    # ── XGBoost ───────────────────────────────────────────────────────────────
    print("\n[1/2] Training XGBoost classifier…")
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="auc",
        random_state=SEED,
        n_jobs=-1,
    )
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    probs = xgb_model.predict_proba(X_test)[:, 1]
    auc   = roc_auc_score(y_test, probs)
    preds = (probs > 0.5).astype(int)
    print(f"  XGBoost AUC: {auc:.4f}")
    print(classification_report(y_test, preds, target_names=["Legit", "Fraud"]))

    path_xgb = MODEL_DIR / "fraud_xgb.pkl"
    with open(path_xgb, "wb") as f:
        pickle.dump(xgb_model, f)
    print(f"  ✓ Saved → {path_xgb}")

    # ── Isolation Forest ──────────────────────────────────────────────────────
    print("\n[2/2] Training Isolation Forest…")
    iso = IsolationForest(
        n_estimators=200,
        max_samples="auto",
        contamination=0.10,
        random_state=SEED,
        n_jobs=-1,
    )
    # Train on LEGIT claims only (unsupervised anomaly detection)
    X_legit = X_train[y_train == 0]
    iso.fit(X_legit)

    scores = iso.decision_function(X_test)
    iso_preds_raw = iso.predict(X_test)           # -1 = anomaly, 1 = normal
    iso_preds = (iso_preds_raw == -1).astype(int) # convert to 0/1

    iso_auc = roc_auc_score(y_test, -scores)      # negate: lower score = more anomalous
    print(f"  Isolation Forest AUC (proxy): {iso_auc:.4f}")
    print(classification_report(y_test, iso_preds, target_names=["Legit", "Fraud"]))

    path_iso = MODEL_DIR / "iso_forest.pkl"
    with open(path_iso, "wb") as f:
        pickle.dump(iso, f)
    print(f"  ✓ Saved → {path_iso}")

    print("\n✅ All models trained and saved successfully.")
    return auc


if __name__ == "__main__":
    train()
