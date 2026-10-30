# AEGIS 360

AEGIS 360 is a local-first analyst workbench for validating tabular data, profiling data quality, comparing observed periods, reviewing statistical outliers, testing baseline forecasts and analyst scenarios, and creating a methodology-aware Excel report.

**Current readiness:** runnable local application and container/deployment preparation are implemented. No public deployment has been created. For confidential or internet-facing business use, put a managed identity-aware proxy in front of the app and complete an organization-specific security review. The built-in shared-password gate is not SSO, RBAC, or a compliance control.

## Capabilities

- Read CSV, XLSX, JSON array/object/JSON Lines, and Parquet files in memory.
- Validate file signatures, unique headers, UTF-8 input, row/column/cell limits, and expanded XLSX/Parquet size.
- Profile types, missing cells, uniqueness, numeric distributions, and exact duplicates.
- Preview explicit duplicate and missing-value cleaning strategies before using cleaned rows.
- Calculate descriptive statistics, category summaries, monthly trends, period variance, Pearson correlations, robust outlier review flags, naive/seasonal-naive forecasts with holdout MAE, and analyst-defined scenarios.
- Export a bounded workbook with an executive summary, KPI summary, dataset profile, quality details, variance, trend, scenario, processing metadata/fingerprint, methodology, and imported values.
- Record SQLite ingestion metadata and SHA-256 fingerprints without persisting source files or source rows.
- Fetch one country and one indicator from the World Bank Indicators API v2 on explicit user request; response size, retries, timeout, year range, and observation count are bounded.
- Run without an AI provider or external data connection.

The bundled sample is synthetic and is generated reproducibly. The World Bank source is separate from uploads and synthetic business data; the app does not merge unrelated grains. World Bank API requests are opt-in, and no user upload is sent to that service. Units, currencies, and business meaning are not inferred from column names. Correlation is not causation, an outlier is not proof of wrongdoing, and scenario outputs are not predictions.

## Windows setup

Use Python 3.12 or 3.13. From this project folder in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev,parquet,auth]'
python scripts\generate_demo_data.py
python -m scripts.doctor
python -m streamlit run src\aegis360\dashboard.py --server.maxUploadSize=25
```

Open the local URL Streamlit prints (normally `http://localhost:8501`). The app uses `data/runtime/aegis360.db` for metadata only. Source files are not saved. Parquet support is included by the optional `parquet` extra.

For local password protection, set `AEGIS_ACCESS_PASSWORD` in the current PowerShell session before starting the app. `AEGIS_ENV=production` additionally requires a password with at least 16 characters. Do not use a shared password as a substitute for a managed identity provider on a public service.

## Configuration

Copy `.env.example` to `.env` only for tools that load dotenv files; the application reads process environment variables. Supported settings:

| Variable | Default | Purpose |
|---|---|---|
| `AEGIS_ENV` | `development` | `development`, `test`, or `production` |
| `AEGIS_LOG_LEVEL` | `INFO` | Standard Python log level; structured logs omit dataset values |
| `AEGIS_DATA_DIR` | `data/runtime` | Directory containing SQLite metadata |
| `AEGIS_MAX_UPLOAD_MB` | `25` | Upload limit; accepted range is 1–25 MB |
| `AEGIS_AUTH_MODE` | `password` | `password` for a restricted prototype or `oidc` for identity-provider sign-in |
| `AEGIS_ACCESS_PASSWORD` | unset | Password-mode gate; required in production password mode |
| `AEGIS_OIDC_ALLOWED_DOMAINS` | unset | Comma-separated email domains authorized in OIDC mode |
| `AEGIS_OIDC_ALLOWED_EMAILS` | unset | Comma-separated exact email addresses authorized in OIDC mode |
| `AEGIS_STREAMLIT_SECRETS_FILE` | unset | Optional mounted TOML file copied to Streamlit's user secrets path at container start |

## Tests and quality checks

```powershell
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m pip_audit --progress-spinner off
```

The tests use deterministic fixtures and mocked public API responses; they do not contact public data sources. CI is configured for Python 3.12/3.13 on Windows, Python 3.12 on Linux, dependency auditing, and a Docker build/health smoke test.

## Container run

```powershell
$env:AEGIS_ACCESS_PASSWORD = 'replace-with-a-unique-secret-at-least-16-chars'
docker compose up --build
```

The container runs as a non-root user, uses a read-only root filesystem with a temporary `/tmp`, enables Streamlit CORS/XSRF protections, and stores only its SQLite metadata in the named `aegis-data` volume. Compose binds to loopback at `http://localhost:8501`; do not expose this plain HTTP port directly to the internet.

## Render deployment preparation

`render.yaml` defines a Docker web service, the Streamlit health-check path, a generated access secret, a 25 MB upload cap, and a persistent disk for the metadata database. Render Blueprints support generated secrets and persistent disks; attached disks are available to paid web services and make the service single-instance with downtime during deploys ([Blueprint reference](https://render.com/docs/blueprint-spec), [disk behavior](https://render.com/docs/disks)).

To deploy, connect the verified GitHub repository to Render, create a Blueprint from `render.yaml`, review the generated secret and service plan, then verify health and logs in the Render dashboard. This workspace has not created or checked a Render service. Password mode is only a temporary barrier; configure and verify the optional OIDC path and access allowlist before allowing confidential company data.

For OIDC, install the `auth` extra (included in the Docker image), register the actual app URL plus `/oauth2callback` with your provider, upload a real secrets file based on [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) through the hosting provider's secret-file facility, and set `AEGIS_AUTH_MODE=oidc` with at least one exact allowed email or domain. The container copies the mounted secret file to its temporary home with owner-only permissions. Configure the provider to enforce MFA if required. A domain allowlist is an access rule, not role-based authorization. Keep password mode until the OIDC callback, sign-in, denied-user, sign-out, and deployment flows have been verified with your actual provider.

See [deployment instructions](docs/deployment.md), [operations runbook](docs/runbook.md), and [threat model](docs/threat-model.md).

## Data and persistence boundary

Uploaded source records and World Bank observations remain in Streamlit session memory only. The SQLite database stores ingestion job IDs, UTC time, status, SHA-256 content fingerprint, row/column counts, duration, and exception class. It does not store source filenames or cell values. The sample file is public project content and synthetic. Production database recovery therefore restores operational history only, not user datasets.

The source catalog is [config/sources.toml](config/sources.toml). The World Bank adapter is covered by mocked-response tests and a bounded live U.S. population request for 2021–2022 returned two observations on 2026-10-30. Source terms and future candidates are described in [source registry notes](docs/source-registry.md).

## Known limitations

- Password mode is a shared gate, not user identity, MFA, roles, rate-limited authentication, or audit-grade authorization. Optional OIDC requires a real provider configuration and allowlist before it is active.
- No AI provider, public REST API for AEGIS itself, scheduled ingestion, PDF export, or multi-user dataset storage.
- SQLite history is local to one service instance; the Render disk configuration does not support horizontal scaling.
- Forecasting is limited to simple naive/seasonal-naive baselines. No confidence interval is claimed.
- Financial and risk metrics are only computed from supplied fields; business semantics require analyst validation.
- Docker build and hosted deployment must be verified in CI/Render; the current local Docker Engine is not accessible from this workspace.

## Portfolio description

Built a local-first Python analytics workbench with bounded tabular ingestion, data-quality profiling, period comparisons, statistical review signals, baseline forecasting, assumption-based scenarios, safe Excel reporting, SQLite operational metadata, container hardening, and CI/deployment configuration. It does not claim production security certification, real customer adoption, model accuracy, or measured business impact.
