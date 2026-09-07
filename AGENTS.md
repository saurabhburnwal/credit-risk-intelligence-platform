# Engineering & Documentation Guidelines

## 1. Technical Submissions & Documentation Tone
- **Factual over Promotional**: Do not generate marketing-style badges, shields, or self-congratulatory "Candidate Verification Checklists" that award the project a score.
- **Defendable Language**: Avoid unearned buzzwords ("production-grade", "enterprise-grade", "industry-standard") unless substantiated by benchmark data or specific architectural constraints.
- **Candid Limitations**: Document "Known Limitations & Trade-offs" honestly and explicitly (e.g., single-table SHAP scope, missingness handling rationale). Do not oversell or use boilerplate future roadmaps.
- **Audience Calibration**: Keep documentation concise and technical (aiming for a 3–5 minute skim for evaluators), directly addressing assignment rubric criteria.

## 2. Ground-Truth Feature & Data Reconciliation
- **Inspect Code First**: Never document data preprocessing, imputation, or feature selection from memory or initial intent. Always verify the active implementation in `src/data/` or `src/ml/`.
- **Explicit Feature Arithmetic**: Always report exact feature breakdowns (e.g., 119 raw + 13 engineered + 5 bureau + 5 prev = 142 total features).
- **Explain Native Handling**: When retaining high-missingness features, explain the model-specific mechanism (e.g., LightGBM histogram binning of NaNs vs. linear baseline medians).

## 3. Repository Hygiene & Zero-Setup Evaluator Bootstrap
- **Zero Data in Git**: Ensure `.gitignore` strictly excludes raw data (`data/*.csv`, `*.csv`), database binaries (`sql/*.db`, `sql/*.db.gz`), secrets (`.env`), and virtual environments (`.venv/`).
- **Clean Evaluator Experience**: The platform must boot cleanly from scratch (`docker compose up` or local `uv run`) without presuming pre-existing local build databases or cached state.

## 4. Efficient & Targeted Testing (No Redundant Full-Suite Runs)
- **Targeted Scope**: Run only the specific test module or case directly touched by recent changes (e.g., `pytest tests/test_ui_redesign.py`) rather than launching the entire heavy ML/SHAP test suite.
- **Strict Change-Triggered Testing Only**: Never run or re-run any test command unless related source or test files were modified since the last passing run. Strictly forbid redundant "final check" or "confirmation" runs if the current code state has already passed.
- **Reserve Full Suite for Final Gates**: Reserve full suite execution strictly for final pre-push or pre-submission verification.
