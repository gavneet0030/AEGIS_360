# Production readiness record

**Review date:** 2026-10-30  
**Application:** AEGIS 360, local-first single-process Streamlit workbench  
**Scope:** Existing project hardening and release preparation; no hosted deployment was created.

## Architecture and data boundaries

- Streamlit serves the dashboard and keeps uploaded files and fetched public observations in per-session memory.
- The parser accepts CSV, XLSX, JSON/JSON Lines, and Parquet; byte, row, column, cell, and expanded archive limits are enforced.
- Analytics are deterministic pandas/NumPy functions. Forecasting uses naive or seasonal-naive baselines; scenario outputs use an explicit analyst assumption.
- Excel output is generated in memory, bounded, escapes formula-like text cells and headers, and records the source fingerprint plus applied cleaning parameters/counts when cleaned values are exported.
- SQLite contains operational job metadata only. It retains at most 10,000 job rows; it never stores uploaded rows or filenames.
- The World Bank adapter is called only on an explicit user request and has bounded timeouts, retries, response bytes, pages, and row counts.
- Password mode is a basic shared gate. Optional OIDC mode requires Streamlit secrets and an exact email/domain allowlist. OIDC has no roles; the provider must enforce any MFA policy.

## Runtime configuration

The supported settings are listed in the project README and `.env.example`. Production password mode requires a 16-character password. Production OIDC mode requires an allowlist and a Streamlit `[auth]` secrets file. The container entrypoint can read a mounted secret file and copies it to a temporary home with owner-only permissions. Never commit the actual `secrets.toml`.

## Test and verification evidence

Record each final verification in the release checklist. Automated tests use synthetic data and mocked World Bank responses; one separate bounded live API request was performed for U.S. population, 2021–2022. Docker configuration and image build are separate checks: only report an image as built after a Docker Engine build completes.

Commands:

```powershell
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m scripts.doctor
python -m pip_audit --progress-spinner off
python -m scripts.benchmark_workloads
```

## Capacity and persistence

The benchmark script creates reproducible synthetic CSV workloads at 1,000, 10,000, and 100,000 rows. It measures ingestion, profile, trend, variance, anomaly, forecast, and workbook generation. `tracemalloc` peak values are additional traced Python allocations; they are not process RSS and exclude the already-created input payload/DataFrame. See [performance benchmarks](performance-benchmarks.md) for measured results and their limitations.

Uploaded data and report downloads are session-bound and are not backed up. The persistent database is operational history only. A Render disk is single-instance storage and causes downtime during deploys; it does not provide horizontal scaling. Review the selected service plan, disk cost, and deployment downtime before creating a service.

## Acceptance status

See [release readiness](release-readiness.md) for a PASS / PARTIAL / BLOCKED / FAIL result against every Phase 2 acceptance criterion. A local pass does not imply that GitHub CI, a container runtime, or a hosted deployment has been verified.
