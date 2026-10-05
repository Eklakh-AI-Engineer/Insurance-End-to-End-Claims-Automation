# ClaimAI Development

## Backend

Python dependencies are defined in backend/requirements.txt.

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Run the backend tests:

```bash
pytest
```

The repository currently contains a focused backend/tests/test_claims.py module. Test counts should be taken from a fresh run rather than inferred from source presence.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Production build:

```bash
npm run build
```

## Docker

```bash
docker compose up --build
```

## ML models

Training scripts are under ml/. Generated model files should remain local and are excluded by .gitignore.

## Environment

Copy .env.example to .env and set provider credentials locally. Never commit .env.

## Development rule

When changing model or decision behavior:

1. update tests;
2. document the policy change;
3. evaluate the affected model;
4. keep model metrics separate from business-policy thresholds;
5. preserve manual review.
