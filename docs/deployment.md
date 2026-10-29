# Deployment guide

## Container requirements

The Docker image uses Python 3.12, installs the pinned application dependencies, runs Streamlit on `0.0.0.0:$PORT`, exposes port 8501 by default, and uses `/_stcore/health`. Container health checks do not require app login. Docker Compose uses a named volume and read-only root filesystem.

Build and run locally:

```powershell
$env:AEGIS_ACCESS_PASSWORD = 'replace-with-a-unique-secret-at-least-16-chars'
docker compose up --build
```

Verify `http://localhost:8501/_stcore/health` returns `ok` and `http://localhost:8501` shows the sign-in screen. Keep the port local or place TLS and identity controls in front of it. Stop with `Ctrl+C`; `docker compose down` retains the named volume, while `docker compose down --volumes` deletes local metadata.

## Render Blueprint

1. Push the reviewed project branch to a GitHub repository that you control.
2. In Render, create a Blueprint using the repository and `render.yaml`.
3. Review the service type, paid plan, persistent disk, generated shared secret, and public route before confirming.
4. Wait for the Docker build and health check.
5. Verify sign-in, sample dashboard, upload limits, report download, and restart persistence in the Render dashboard.
6. Add a managed identity-aware access proxy and custom domain/TLS policy before confidential or organizational use.

The Blueprint uses a persistent disk for the operational SQLite database. Render documents persistent disks as paid-service storage, single-instance, and incompatible with zero-downtime deploys; plan capacity and downtime accordingly. The source records themselves are not persisted.

## Environment

Set `AEGIS_ENV=production`, `AEGIS_DATA_DIR=/var/data`, `AEGIS_MAX_UPLOAD_MB=25`, and a strong `AEGIS_ACCESS_PASSWORD`. The Docker command maps the platform `PORT` variable to Streamlit. Never place a real secret in `render.yaml`, CI logs, or Git. Rotate the shared password after staff changes and restrict who can read service environment values.

## Rollback and recovery

- Roll back by selecting the last known-good deploy in the platform deploy history.
- The metadata database contains job metadata only. Source datasets and generated reports are ephemeral and are not recoverable after the browser session ends.
- Before manual metadata repair, stop the service and copy `/var/data/aegis360.db` using SQLite's backup API; do not copy a live SQLite database file while writes are active.
- Render disk snapshots are platform recovery aids, not an application-level verified backup. Test restoration and access policy in the hosting account before relying on them.

No cloud deployment has been created from this workspace. Deployment still requires an authorized hosting account, reviewed public-access policy, and a connected GitHub repository.
