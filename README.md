# ClaimAI — Insurance Claims Automation Prototype

> **An end-to-end insurance-claims automation prototype combining document extraction, fraud scoring, image analysis, payout estimation, and a review/settlement decision path.**

ClaimAI is a prototype/hackathon-style system demonstrating how heterogeneous claim evidence can be processed through a FastAPI backend, ML services, and a React frontend.

It should **not** be presented as a production insurance adjudication system.

## Current scope

| Capability | Status |
|---|---|
| FastAPI backend | Implemented |
| React + Vite frontend | Implemented |
| PostgreSQL / SQLAlchemy model layer | Implemented |
| Claim submission API | Implemented |
| Fraud scoring | Implemented |
| Image-analysis pipeline | Implemented |
| Payout estimation | Implemented |
| LLM/OCR provider integration | Implemented with configurable provider |
| Admin dashboard / claims view | Implemented |
| Docker Compose | Implemented |
| Model training scripts | Present |
| Automated settlement decision rule | Implemented as prototype logic |
| Production model validation | **Not claimed** |
| Production insurance authorization | **Not claimed** |
| Regulatory/compliance certification | **Not claimed** |

## Architecture

```text
Claim submission
      |
      v
FastAPI
      |
      +--> OCR / document extraction
      |
      +--> Fraud scoring
      |      XGBoost + Isolation Forest
      |
      +--> Image analysis
      |
      +--> Payout estimation
      |      Gradient Boosting
      |
      v
Decision policy
   |          |
   v          v
Approve    Manual Review
      |
      v
Persistence + audit/fraud records
```

The decision policy currently uses configurable thresholds:

```text
fraud_score < FRAUD_THRESHOLD
AND
payout_match >= PAYOUT_MATCH_THRESHOLD
AND
image_valid
```

This is a **prototype decision rule**, not a validated insurance underwriting policy.

## AI / ML components

| Component | Current implementation |
|---|---|
| OCR / extraction | OpenAI or Gemini provider abstraction |
| Fraud model | XGBoost + Isolation Forest |
| Image analysis | OpenCV / image-model pipeline |
| Payout model | GradientBoostingRegressor |
| Decision policy | Explicit threshold-based rule |

Model training scripts are under ml/.

Generated model artifacts are excluded from source control.

### Model claims

The previous README documented approximate training outputs such as AUC and payout MAE. Those figures are **not treated as current benchmark results** in this README.

For recruiter-facing claims, report a metric only when its dataset, split, evaluation procedure, and reproducible run are available.

## Quick start

### 1. Configure

```bash
git clone https://github.com/Eklakh-AI-Engineer/Insurance-End-to-End-Claims-Automation.git
cd Insurance-End-to-End-Claims-Automation
cp .env.example .env
```

Set local development credentials in .env. Never commit .env.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API documentation: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Docker

```bash
docker compose up --build
```

## API surface

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/submit-claim | Submit a claim and supporting files |
| POST | /api/check-fraud | Re-run fraud analysis |
| GET | /admin/dashboard | Dashboard aggregates |
| GET | /admin/claims | Claims listing |
| GET | /admin/heatmap | Fraud-score visualization data |
| GET | /health | Service health |

The implementation under backend/routes/ is the authoritative source for request/response behavior.

## Project structure

```text
ClaimAI/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routes/
│   ├── services/
│   └── tests/
├── frontend/
├── ml/
│   ├── data/
│   ├── models/
│   ├── train_fraud_model.py
│   └── train_payout_model.py
├── docker-compose.yml
├── .env.example
└── docs/
```

## Security

The previous repository state included a tracked .env file. This maintenance removes it, adds .env to .gitignore, and provides .env.example.

The inspected environment file used a local PostgreSQL host and had empty OpenAI/Gemini API-key fields; nevertheless, environment files should never be committed.

See docs/SECURITY.md.

## Important limitations

ClaimAI is a prototype:

- fraud scores are model outputs, not proof of fraud;
- image validity is not a substitute for human claims investigation;
- payout estimates are model estimates, not contractual entitlement;
- automated approval is not a regulated insurance determination;
- no regulatory certification is claimed;
- no independent production model validation is claimed;
- model performance should not be inferred from the presence of training scripts.

## Engineering principles

1. Keep extraction, fraud, image, payout, and decision stages explicit.
2. Keep model outputs distinguishable from business policy.
3. Make thresholds configurable.
4. Never commit secrets or generated model binaries.
5. Preserve a manual-review path.
6. Report reproducible metrics only.
7. Treat production insurance authorization as a separate governance problem.
