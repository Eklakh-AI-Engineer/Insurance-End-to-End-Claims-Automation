# ClaimAI Evaluation

## Evaluation policy

ClaimAI should report model performance only with enough context to reproduce the result:

- dataset;
- train/validation/test split;
- preprocessing;
- random seed;
- metric definition;
- model version;
- evaluation date.

## Existing model claims

Earlier README content listed approximate outputs such as fraud AUC and payout MAE. Those values are not treated as current benchmark results by the maintained documentation because the repository does not currently provide a complete, versioned evaluation report establishing the dataset, split, and procedure behind those figures.

Do not quote those values as recruiter-facing performance metrics without reproducing and documenting the evaluation.

## Pipeline-level evaluation

### Fraud

- ROC-AUC / PR-AUC;
- calibration;
- false-positive rate;
- false-negative rate;
- threshold sensitivity.

### Image analysis

- classification precision/recall;
- image-quality failure rate;
- robustness across damage/image conditions.

### Payout

- MAE / RMSE;
- error by claim type;
- residual analysis;
- calibration against human-approved amounts.

### Decision policy

Evaluate the policy separately from the models:

- auto-approval rate;
- manual-review rate;
- false-approval rate;
- false-review rate;
- threshold sensitivity.

A model metric is not evidence that the end-to-end approval policy is safe.
