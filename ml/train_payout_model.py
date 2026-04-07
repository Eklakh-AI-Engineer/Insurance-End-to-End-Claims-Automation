"""
train_payout_model.py
=====================
Trains a GradientBoostingRegressor to estimate fair insurance payouts.

Run:  python ml/train_payout_model.py
"""
from __future__ import annotations
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

SEED = 42
N_SAMPLES = 5_000
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

np.random.seed(SEED)

CLAIM_TYPE_MAP = {"health": 0, "auto": 1, "property": 2, "life": 3, "travel": 4}

# Historical payout rates per claim type (ground truth for simulation)
BASE_RATES = {"health": 0.82, "auto": 0.74, "property": 0.68, "life": 0.90, "travel": 0.65}


def generate_payout_data(n: int = N_SAMPLES) -> pd.DataFrame:
    claim_types = np.random.choice(list(CLAIM_TYPE_MAP.keys()), n)
    enc_types   = np.array([CLAIM_TYPE_MAP[c] for c in claim_types])
    base_rates  = np.array([BASE_RATES[c] for c in claim_types])

    amounts         = np.abs(np.random.lognormal(mean=9, sigma=1.2, size=n))
    history_count   = np.random.poisson(lam=1.5, size=n)
    days_last       = np.random.exponential(scale=200, size=n).astype(int) + 1
    fraud_scores    = np.random.beta(2, 8, size=n)  # mostly low (legit data)

    # Simulated payout
    fraud_penalty   = fraud_scores * 0.30
    freq_penalty    = 0.05 * (history_count >= 3).astype(float)
    actual_rate     = np.clip(base_rates - fraud_penalty - freq_penalty, 0.05, 1.0)

    payouts = amounts * actual_rate + np.random.normal(0, amounts * 0.02)
    payouts = np.clip(payouts, 0, amounts)

    df = pd.DataFrame({
        "claim_type_enc":       enc_types,
        "requested_amount":     amounts,
        "history_claim_count":  history_count,
        "days_since_last_claim":days_last,
        "fraud_score":          fraud_scores,
        "actual_payout":        payouts,
    })
    return df


def train():
    print("=" * 60)
    print("  Insurance Payout Estimator — Model Training")
    print("=" * 60)

    df = generate_payout_data()
    print(f"✓ Generated {len(df)} synthetic payout records")
    print(f"  Mean requested: ${df['requested_amount'].mean():,.0f}")
    print(f"  Mean payout:    ${df['actual_payout'].mean():,.0f}")

    feature_cols = ["claim_type_enc", "requested_amount", "history_claim_count",
                    "days_since_last_claim", "fraud_score"]
    X = df[feature_cols].values
    y = df["actual_payout"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=SEED,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2  = r2_score(y_test, preds)
    print(f"\n  MAE:  ${mae:,.2f}")
    print(f"  R²:   {r2:.4f}")

    path = MODEL_DIR / "payout_model.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"\n  ✓ Saved → {path}")
    print("\n✅ Payout model trained and saved.")
    return mae


if __name__ == "__main__":
    train()
