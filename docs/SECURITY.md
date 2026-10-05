# ClaimAI Security

## Secrets

The repository previously tracked a .env file. The maintenance baseline removes it and adds .env to .gitignore.

Use .env.example for local configuration.

If a real credential was ever committed, rotate it even after removing the file because Git history can retain old content.

## Sensitive claim data

Insurance claims can contain personal, financial, medical, and document data.

Development guidance:

- use synthetic data;
- do not commit real claim documents;
- avoid sensitive data in logs;
- restrict database access;
- limit upload size and file types;
- review external OCR/LLM provider data handling.

## AI / ML safety

Model output is probabilistic.

- Fraud score is not proof of fraud.
- Image validity is not proof of authenticity.
- Payout estimate is not entitlement.
- LLM extraction is not authoritative evidence.

The system should retain a manual-review path for uncertain or high-risk cases.

## Production security boundary

This repository does not claim regulatory certification, production penetration testing, formal model-risk governance, independent model validation, or production-grade privacy controls.
