# Testing strategy

## Local quality gate

Run:

```powershell
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m pip_audit --progress-spinner off
```

The suite uses small deterministic DataFrames and in-memory CSV, XLSX, JSON, Parquet, and workbook payloads. Pytest uses an ignored `.pytest-tmp` directory under the project because the managed Windows test environment restricts its system temp directory. The regression suite also runs a Streamlit AppTest through initial dashboard render and report generation, plus an OIDC missing-configuration fail-closed check.

## CI

`.github/workflows/ci.yml` tests Python 3.12 on Ubuntu and Python 3.12/3.13 on Windows. CI installs the pinned production graph in `requirements-production.lock` as constraints. A separate Ubuntu job builds the image and checks the Streamlit health route. `.github/workflows/security.yml` audits the exact pinned production graph with `pip-audit` on pull requests and weekly. Dependabot checks Python and Actions dependencies.

## Limits

No live external APIs are contacted. The dashboard smoke test checks the Streamlit script runs and exposes core widgets; it does not replace manual browser review. The container build job is configured but has not run in this workspace because the Docker daemon pipe is inaccessible.
