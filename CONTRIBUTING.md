# Contributing

## Local setup

Use Python 3.12 or 3.13 and follow the Windows instructions in [README.md](README.md). Install development and optional Parquet dependencies with:

```powershell
python -m pip install -e '.[dev,parquet]'
```

## Before a change is ready

```powershell
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m pip_audit --progress-spinner off
```

Changes to an analytical calculation must include a definition, boundary behavior, a regression test, and a methodology update. Parser changes must retain bounded resource use and add malformed-input tests. Do not add real business data, credentials, generated reports, or a notebook to Git.

## Pull requests

Keep changes focused. Include actual verification results, note unverified platform or network behavior, and avoid business-impact claims without evidence. Public-source adapters require source terms, grain, stable keys, limits, provenance, and mocked integration tests.
