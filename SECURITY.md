# Security policy

## Supported deployment posture

AEGIS 360 is a local-first single-user analyst prototype. The shared-password option is a basic access gate. It is not a hardened authentication system and does not provide SSO, MFA, per-user authorization, role management, rate limiting, or compliance certification. Use a managed identity-aware proxy before exposing it to an organization or confidential data.

## Reporting a vulnerability

Do not include real dataset values, credentials, or private exports in public issues. The current repository has no verified private security-advisory contact configured. Until one is configured, do not publish exploit details; contact the repository owner through a private channel they have independently confirmed.

## Security controls in the current code

- Upload extensions and actual signatures are checked before parsing.
- Uploads are bounded by byte size, rows, columns, total cells, and format-specific expansion limits.
- XLSX files are opened read-only with formulas not evaluated; macro-enabled workbooks are rejected.
- Uploaded files and row values are not written to disk or logs.
- Excel string cells and column headers are escaped against formula injection.
- Production mode requires a configured access password of at least 16 characters.
- SQLite statements use parameters and store operational metadata only.
- Docker uses a non-root user, read-only root, dropped capabilities, and a separate data volume.
- CI runs pinned dependency checks and a scheduled vulnerability audit.

These controls do not replace independent security review, managed identity, network policy, secret rotation, backup/recovery testing, or platform patching.
