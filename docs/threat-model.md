# Threat model

## Assets

- Uploaded business records displayed in the current Streamlit session.
- Local SQLite operational metadata and content fingerprints.
- Optional shared access password.
- Generated Excel exports.

## Trust boundaries and controls

| Boundary | Threat | Current control | Residual limitation |
|---|---|---|---|
| Browser upload → parser | Oversized, malformed, mislabeled, duplicate-header, or archive-bomb file | Extension allowlist, content signatures, UTF-8/duplicate checks, 25 MB cap, row/column/cell caps, XLSX/Parquet expansion limits | Streamlit holds upload bytes in memory before parser validation; reverse proxy and server resource limits remain necessary |
| Spreadsheet → Excel report | Formula injection | Text values and headers beginning with formula markers after leading whitespace are prefixed with an apostrophe | Other spreadsheet viewer-specific interpretation should be reviewed before new formats are added |
| User → dashboard | Unauthorized access | Optional constant-time shared-password comparison; production mode fails without 16+ characters | No identity, MFA, RBAC, per-user audit, rate limiting, or session revocation; use a managed identity proxy before public/confidential use |
| Container → host | Container compromise or writes outside data | Non-root UID, read-only root, dropped Linux capabilities, no-new-privileges, temporary `/tmp`, dedicated data volume | Container image and host require ongoing patching; image scan not run locally |
| App → metadata store | SQL injection, accidental source-data persistence | Parameterized SQL, fixed queries, source file/rows not written | SQLite metadata is single-instance and relies on persistent-volume backup |
| Logs | Sensitive values or credentials in logs | Structured allowlisted fields; no records, filenames, or password are logged | Platform logs still require access controls and retention policy |

## Excluded controls and claims

This project does not claim compliance certification, independent penetration testing, formal threat-model review, hardened multi-tenant authorization, encrypted source-data retention, or production identity management. Do not deploy confidential data to a public service until those controls are designed for the intended organization.
