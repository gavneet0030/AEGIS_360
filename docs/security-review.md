# Security review

**Review date:** 2026-10-30  
**Scope:** Source-level review of the current single-user Streamlit application, parser, Excel export, metadata store, container configuration, and deployment blueprint. This is not a penetration test or certification.

## Controls verified in code

- The upload layer allowlists CSV, XLSX, JSON, and Parquet, checks signatures, rejects duplicate/empty headers, and enforces upload, row, column, cell, and expanded archive limits.
- CSV and JSON are parsed as UTF-8; duplicate JSON object keys are rejected. XLSX opens read-only with cached values, rejects macro-enabled content, and applies an expanded-size limit. Parquet metadata is checked before materialization.
- Parsing happens from in-memory bytes; the application does not write uploaded rows or filenames to SQLite or logs.
- Excel export prefixes text headers and cells that could be interpreted as formulas. Tests load the generated workbook and inspect cell values.
- Database operations use SQLite parameter binding. Stored fields are limited to job ID, UTC time, status, SHA-256 fingerprint, dimensions, duration, and exception class. The history is capped at 10,000 rows.
- JSON logs use an allowlist of operational fields. Passwords, row values, names, and raw exception messages are not emitted by application event logs.
- Containers run as UID 10001, use a read-only root, drop Linux capabilities, enable no-new-privileges, use a dedicated writable data mount, and configure Streamlit CORS/XSRF protections. Compose binds its host port to loopback.
- Password mode fails closed in production without a long secret. Optional OIDC mode requires provider configuration and an explicit verified-email allowlist; missing secrets or unverified/disallowed identity claims are rejected.

## Findings and residual risks

| Finding | Severity | Treatment / residual risk |
|---|---|---|
| Shared-password mode is not user identity, MFA, authorization, rate limiting, or session revocation. | High for internet-facing confidential use | Optional OIDC plus exact email/domain allowlist is implemented. A real identity provider, callback URL, allowlist, and provider-side MFA policy still require configuration and end-to-end verification. |
| OIDC email verification and session behavior depend on the provider and Streamlit's identity cookie. | Medium | The app requires an `email_verified` claim and allowlist match. Current Streamlit documentation states the identity cookie expires after 30 days and logout does not terminate already-open sessions in other tabs. Test provider revocation and session behavior before organizational use. OIDC does not provide roles in this app. |
| SHA-256 dataset fingerprints can link repeated files and may be guessable for low-entropy datasets. | Medium | No cell values are stored, but restrict access to the SQLite file and backups as potentially sensitive metadata. |
| Streamlit receives uploaded bytes before application-level validation; parsing can use multiple in-memory copies. | Medium | Upload and shape limits bound inputs. Reverse-proxy limits and platform memory capacity remain necessary; see benchmark limitations. |
| XLSX/Parquet expansion checks do not eliminate every parser/library vulnerability. | Medium | Runtime dependency pins and the scheduled/PR audit reduce known exposure; keep CI security checks enabled and refresh the lock when dependencies change. |
| Render web services are publicly reachable by default; a generated password does not create an identity-aware boundary. | High for confidential data | Do not deploy sensitive datasets until OIDC is configured and the public route/access policy is reviewed. No hosted service was created in this review. |
| OIDC allowlisted users share the application-wide operational ingestion history. | Medium | The app is not a multi-tenant product and has no per-user history authorization. Restrict the allowlist to a trusted group and do not expose sensitive fingerprints or counts until this boundary is redesigned. |
| Container build, image scan, live OIDC flow, and hosted proxy configuration could not be verified here. | Blocked | Docker Engine access and provider credentials are not available. |

## Dependency audit

**Completed 2026-10-30:** `pip-audit 2.10.1` checked all 45 pinned packages in `requirements-production.lock` against PyPI vulnerability data using `--disable-pip --no-deps`. An initial direct scan found six advisory records for Streamlit 1.51.0 and PyArrow 21.0.0. A subsequent 46-package graph scan found 105 advisory records across AnyIO 4.10.0, Certifi 2026.5.20, Cryptography 46.0.3, IDNA 3.11, Pillow 12.0.0, and urllib3 2.5.0; the source data included duplicate alias records. The project now pins Streamlit 1.66.1, PyArrow 26.0.0, AnyIO 4.14.2, Certifi 2026.10.19, Cryptography 50.0.0, IDNA 3.15, Pillow 13.0.0, and urllib3 2.8.0. The final scan reported **no known vulnerabilities** in the 45-package runtime graph. The lock pins versions but does not include artifact hashes; CI and the Docker build apply those constraints. Reaudit on every lock update and scheduled CI run.

Reproduce the runtime audit after installing the project security extra:

```powershell
python -m pip install -c requirements-production.lock -e ".[security,parquet,auth]"
python -m pip_audit -r requirements-production.lock --disable-pip --no-deps --progress-spinner off
```

## Review boundary

This review did not include a penetration test, third-party component scan of a built image, network exposure scan, review of an actual identity-provider tenant, or verification of backups on a hosted disk. Do not claim compliance certification or production approval from this document alone.
