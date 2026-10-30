# Operations runbook

## Start locally

From the project root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -c requirements-production.lock -e ".[dev,parquet,auth]"
python scripts\generate_demo_data.py
python -m scripts.doctor
python -m streamlit run src\aegis360\dashboard.py --server.maxUploadSize=25
```

Use the local Streamlit URL printed in the terminal. The included CSV is deterministic synthetic data. Uploaded records remain in the current session; do not expect them to survive session loss or restart.

## Container startup and health

After Docker Engine is available, set a unique production-mode password for a restricted prototype and run:

```powershell
$env:AEGIS_ACCESS_PASSWORD = 'replace-with-a-unique-secret-at-least-16-chars'
docker compose up --build
```

The Compose port is loopback-only. Check `http://localhost:8501/_stcore/health` for the Streamlit health endpoint and open `http://localhost:8501` for the dashboard. Use `docker compose logs --follow` for stdout/stderr. Logs are JSON with timestamps, event, status, dimensions, duration, and error class; they must not include file contents, names, passwords, or identity claims.

For Render OIDC, create a secret file containing the real `[auth]` configuration, set `AEGIS_STREAMLIT_SECRETS_FILE=/etc/secrets/<filename>`, `AEGIS_AUTH_MODE=oidc`, and an explicit allowlist. Register the exact HTTPS callback URL with the provider. Verify denied-user behavior, verified email claims, sign-in, sign-out, multiple sessions, and the identity provider's MFA/session policy before permitting sensitive work.

## Diagnostics

- Startup failure: run `python -m scripts.doctor`; inspect required environment values and writable metadata path.
- Upload rejected: inspect the displayed validation message, format signature, UTF-8 encoding, and documented byte/row/column/cell limits. Keep limits enabled.
- World Bank fetch failed: review the safe event's error class/duration, retry availability, selected country/indicator/year range, and public API status. A failure must not be treated as zero values.
- Metadata warning: verify the SQLite path is writable and the data volume is mounted. Analytics may still run without history; do not recreate the database until it is backed up.
- Slow workbook generation: compare current row/cell counts with [measured workloads](performance-benchmarks.md); reduce the data extract when memory is constrained.
- Health is green but UI unavailable: inspect application startup logs and verify the dashboard process is listening on `PORT`.

## Backup and restore

The database contains job metadata and dataset fingerprints, not recoverable datasets. Treat it and its backups as potentially sensitive operational data. Before copying a live SQLite file, stop writes and use SQLite's backup API or a consistent volume snapshot. Verify restore into a separate path with `python -m scripts.doctor` and a read-only `PRAGMA quick_check`. Do not restore source files because the application does not persist them.

Render's attached disk is single-instance and deployment may cause downtime. Its availability, backup policy, cost, and restore process must be verified in the actual account. Keep an application export or off-service backup plan if job history matters.

## Incident handling and rollback

1. Restrict or remove public access first if an identity, secret, or dataset exposure is suspected.
2. Rotate compromised credentials at the identity provider/platform; do not paste secrets into issues or logs.
3. Preserve safe diagnostic logs and timestamps, but do not collect uploaded rows or workbook exports unless explicitly authorized and securely handled.
4. Roll back to the last reviewed deployment only after verifying the access boundary and database compatibility.
5. Record the cause, affected credentials/data, recovery, and follow-up tests in the organization's private incident process.
