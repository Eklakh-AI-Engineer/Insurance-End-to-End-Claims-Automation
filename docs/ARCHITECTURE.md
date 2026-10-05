# ClaimAI Architecture

## Pipeline

```text
Claim submission
      |
      v
FastAPI API
      |
      +--> document / OCR extraction
      |
      +--> fraud scoring
      |      XGBoost + Isolation Forest
      |
      +--> image analysis
      |
      +--> payout estimation
      |      GradientBoostingRegressor
      |
      v
Decision policy
   |          |
   v          v
Approved   Manual Review
      |
      v
Database + audit/fraud records
```

## Decision boundary

The current prototype uses:

```text
fraud_score < fraud_threshold
AND
payout_match >= payout_match_threshold
AND
image_valid
```

The decision rule is explicit and configurable. It is not equivalent to a production underwriting policy.

## Service boundaries

The backend separates route handling, configuration, persistence, OCR, fraud analysis, image analysis, and payout estimation.

The frontend consumes the API and presents claim submission/admin workflows.

## Model boundary

ML model outputs are inputs to policy logic. They should not be represented as ground truth.

A production system would require model validation, calibration, drift monitoring, human-review policy, fairness analysis, and regulatory/governance review.
