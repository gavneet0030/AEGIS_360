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
| XLSX/Parquet expansion checks do not eliminate every parser/library vulnerability. | Medium | Run the dependency audit and update dependencies on findings; keep CI security checks enabled. |
| Render web services are publicly reachable by default; a generated password does not create an identity-aware boundary. | High for confidential data | Do not deploy sensitive datasets until OIDC is configured and the public route/access policy is reviewed. No hosted service was created in this review. |
| OIDC allowlisted users share the application-wide operational ingestion history. | Medium | The app is not a multi-tenant product and has no per-user history authorization. Restrict the allowlist to a trusted group and do not expose sensitive fingerprints or counts until this boundary is redesigned. |
| Container build, image scan, live OIDC flow, and hosted proxy configuration could not be verified here. | Blocked | Docker Engine access and provider credentials are not available. |

## Dependency audit

The audit is **not complete**. `pip-audit==2.10.1` was staged in an isolated target directory, but installing its transitive dependencies stalled and `python -m pip_audit` fails because `pip_api` is missing. No vulnerability-free claim is made. `python -m pip check` passed and confirms dependency consistency only; it is not a vulnerability audit. Retry `python -m pip install -e '.[security,parquet,auth]'` in a network-enabled Python 3.12/3.13 environment, then run `python -m pip_audit --progress-spinner off` and review the complete output before release.

## Review boundary

This review did not include a penetration test, third-party component scan of a built image, network exposure scan, review of an actual identity-provider tenant, or verification of backups on a hosted disk. Do not claim compliance certification or production approval from this document alone.
