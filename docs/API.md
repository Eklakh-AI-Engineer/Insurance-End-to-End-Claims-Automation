# ClaimAI API

## Current endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/submit-claim | Submit claim data and files |
| POST | /api/check-fraud | Re-run fraud analysis |
| GET | /admin/dashboard | Dashboard aggregates |
| GET | /admin/claims | Paginated claims |
| GET | /admin/heatmap | Fraud-score visualization |
| GET | /health | Health check |

The route implementation under backend/routes/ is authoritative.

## Claim submission

The submission endpoint accepts multipart claim data including claim type, description, requested amount, claimant identity/contact fields, optional policy/incident fields, and image/PDF files.

The backend configuration enforces an upload-size limit.

## Decision responses

The API should distinguish model outputs, policy decision, settlement amount, and manual-review state.

A decision response must not be interpreted as regulated insurance adjudication without the necessary external governance and review controls.
