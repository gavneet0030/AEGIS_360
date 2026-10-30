# Production deployment runbook

## Current state

No cloud service has been deployed. The repository's `render.yaml` is a deployment blueprint, not evidence of a live service. It defines a Docker web service on Render's `starter` plan with a 1 GB persistent disk mounted at `/var/data`, a `/_stcore/health` health check, and a generated shared password. No Render service, deployment URL, or live OIDC provider was verified on 2026-10-30. The Render plan and disk can incur cost; review current pricing and approve the cost in the Render account before provisioning.

The local Docker daemon was present but its API named pipe denied access. Therefore the production image, Compose container, container health, upload/analytics/export workflows, persistence across restart, logs, non-root identity, read-only root, and clean shutdown remain unverified. See [final verification](final-verification.md).

## Release gates

1. Restore GitHub CLI or GitHub App write access. Fetch and reconcile remote `main` safely, retain existing history, create a release branch, run the project checks, push, open a pull request, and verify required CI. Do not force-push.
2. Restore Docker Engine API access on a trusted build host. Build the actual Dockerfile, run the Compose configuration, and complete every container check in the verification checklist. Preserve the `aegis-data` volume; do not use `docker compose down --volumes` for routine shutdown.
3. Decide whether the intended deployment may process confidential data. The current password mode is a shared gate, not SSO, MFA, RBAC, or a compliance control. Keep confidential-data access blocked until a real identity provider, explicit allowlist, user lifecycle policy, and required security review are configured and verified.
4. Obtain authorized Render account access and review service plan, region, public exposure, persistent disk size, backup/recovery expectations, environment values, and expected charges. Do not create paid infrastructure until the owner approves its cost.

## Render deployment procedure (not yet executed)

1. In the authorized Render account, connect `https://github.com/gavneet0030/AEGIS_360` after the reviewed release branch is available. Select the repository Blueprint and `render.yaml`.
2. Review the proposed service name, region, plan, disk, generated secret, environment variables, health path, and public URL. Record cost approval before creating a paid service.
3. Deploy and inspect the build logs. Confirm the image starts as the configured non-root user and that `/_stcore/health` becomes healthy.
4. Test sign-in, the synthetic sample dashboard, a safe sample upload, data quality/analytics, and Excel export. Verify no sample source data is retained in SQLite.
5. Restart or redeploy and confirm SQLite operational metadata remains on the mounted disk. Confirm that uploaded source records and generated reports are not promised as persistent.
6. Review logs for accidental data exposure and confirm the service remains healthy. Record the actual Render service name, deploy commit, UTC verification time, and URL only after observing them in the account.

Do not claim deployment success or provide a guessed URL before these checks complete.

## OIDC configuration and verification

OIDC is optional in code but not live-verified. Before enabling it, register the exact HTTPS service URL and `/oauth2callback` with the chosen identity provider; configure provider secrets using the host's secret-file facility; set `AEGIS_AUTH_MODE=oidc` and an explicit email/domain allowlist; and keep credentials out of source control and logs. Require verified email claims and apply the organization's MFA and account lifecycle policies at the provider.

With a real test account and denied account, verify login and redirect, callback state and nonce handling, verified-email and allowlist enforcement, session expiry, logout, protected page access, and role restrictions if roles are implemented. The current app has no role-based authorization. Do not represent an email allowlist as RBAC. Keep confidential data blocked until these checks and the organization's security review pass.

## Recovery and operations

Use the existing [deployment guide](deployment.md) and [operations runbook](operations-runbook.md) for health checks, rollback, SQLite handling, and operational response. The database stores ingestion metadata and fingerprints only; it does not contain uploaded records. Validate the platform's disk recovery process before relying on it. The Render disk configuration is single-instance and constrains deployment availability/scaling; plan and communicate maintenance windows.
