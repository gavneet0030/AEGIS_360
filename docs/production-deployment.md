# Production deployment runbook

## Current release state

The candidate is available on [`codex/phase-3-final-release`](https://github.com/gavneet0030/AEGIS_360/tree/codex/phase-3-final-release) at `a271d4abc96cf2ba75e063e563ccda007a9304d3`, with [PR #1](https://github.com/gavneet0030/AEGIS_360/pull/1) open into `main`. All five checks passed on that head, including a Docker image build and health smoke. PR #1 is merged. The CI container check does not cover Compose, uploads, exports, or persistence.

No cloud service has been deployed. The existing `render.yaml` is a Blueprint, not evidence of a live service. It defines a Docker web service on Render's `starter` plan, a 1 GB persistent disk, a health check, and a generated shared password. No Render service or deployment URL was verified. The plan and disk can incur cost; review current pricing and obtain explicit cost approval before provisioning.

The local Docker daemon's named pipe denied API access, so local Compose execution is unavailable. Live OIDC has not been configured. Keep confidential-data access blocked until identity and access controls are configured and verified.

## Remaining release and deployment gates

1. Complete the PR review and merge only under the repository's review policy. Do not force-push.
2. Run the complete Compose integration checklist on a Docker host with Engine access: health/dashboard, safe sample upload, analytics, Excel export, SQLite persistence after restart, logs, non-root identity, read-only root, and clean shutdown. Preserve the existing `aegis-data` volume; do not use `docker compose down --volumes` for routine shutdown.
3. Configure a real OIDC provider and test login, callback state/nonce, verified email and allowlist enforcement, expiration, logout, protected pages, and implemented role restrictions. The current email allowlist is not RBAC. Keep confidential-data access blocked until these checks pass.
4. Obtain authorized Render access. Review service plan, region, public exposure, disk, backup/recovery, environment values, and expected charges. Do not provision paid infrastructure without explicit cost approval.

## Render deployment procedure (not yet executed)

1. In the authorized Render account, select the verified repository and Blueprint from `render.yaml` after the release branch is approved/merged as required by your release policy.
2. Review the proposed service name, region, plan, persistent disk, generated secret, environment variables, health path, and public URL. Record the cost approval before creating a paid service.
3. Deploy and inspect build logs. Confirm the image starts as its configured non-root user and `/_stcore/health` becomes healthy.
4. Test sign-in using a real configured provider, a denied account, the synthetic sample dashboard, safe sample upload, data quality/analytics, and Excel export.
5. Restart or redeploy and confirm SQLite operational metadata remains on the mounted disk. Uploaded source records and generated reports are not persisted by the application.
6. Review logs for data exposure and confirm service health. Record the actual service name, deploy commit, UTC verification time, and URL only after observing these in the Render account.

Never claim deployment success or provide a guessed URL.

## OIDC configuration and verification

OIDC exists in the application but is not live-verified. Register the exact HTTPS service URL and `/oauth2callback` with the provider; configure provider secrets using the host's secret-file facility; set `AEGIS_AUTH_MODE=oidc` and an explicit email/domain allowlist. Require verified email claims and use provider-enforced MFA and lifecycle policy as required. Keep credentials out of source control and logs.

With an allowed test account and a denied account, verify login/redirect, callback state and nonce, verified-email and allowlist enforcement, session expiry, logout, protected page access, and role restrictions if roles are implemented. The current app has no role-based authorization. Do not represent an email allowlist as RBAC.

## Operations and persistence

Use the [deployment guide](deployment.md) and [operations runbook](operations-runbook.md) for health checks, rollback, SQLite handling, and incident response. SQLite stores ingestion metadata and fingerprints only; it does not contain uploaded records. The Render disk configuration is single-instance and constrains availability/scaling; verify recovery and communicate maintenance expectations before production use.
