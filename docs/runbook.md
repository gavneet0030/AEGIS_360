# Operations runbook

## Health and startup

- Container/platform health route: `GET /_stcore/health`.
- Application port: `PORT` (defaults to 8501 in the image).
- Logs are JSON on stdout/stderr; fields are allowlisted and exclude data rows, filenames, and credentials.
- Metadata database: `${AEGIS_DATA_DIR}/aegis360.db`.

## Common incidents

| Symptom | Check | Response |
|---|---|---|
| App fails to start in production | `AEGIS_ENV`, `AEGIS_ACCESS_PASSWORD`, `PORT`, data directory permissions | Set production values in secret/environment settings, verify writable metadata directory, restart once |
| Upload rejected | File extension/signature, UTF-8 encoding, 25 MB limit, schema, row/column/cell cap | Re-save a supported tabular file; inspect the displayed validation error; do not disable the limits |
| Parquet rejected | Installed `pyarrow`, `PAR1` signature, row/cell/expanded-size caps | Install the `parquet` extra in the image or convert to CSV/XLSX |
| Job history not written | Data volume mounted and writable; available disk space; SQLite error type in logs | Restore writable persistent storage; analysis can continue without metadata history |
| Workbook download fails | Data rows <=250,000, memory and disk pressure | Use a smaller extract; do not increase limits without capacity testing |
| Outlier appears | Selected filters, robust score, observation and baseline | Investigate data quality/context; a flag is not proof of fraud or cause |

## Routine tasks

- Review deploy health, structured errors, and disk use after each release.
- Audit the weekly dependency workflow and Dependabot alerts.
- Rotate environment secrets after suspected exposure or staff access changes.
- Test backup/restore and rollback before relying on them for production continuity.
- Do not add scale-out instances while storing SQLite on a local persistent disk.
