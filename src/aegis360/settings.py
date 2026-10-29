"""Validated environment configuration for local and container deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    environment: str
    log_level: str
    data_dir: Path
    max_upload_mb: int
    access_password: str | None

    @property
    def database_path(self) -> Path:
        return self.data_dir / "aegis360.db"


def load_settings() -> Settings:
    """Read and validate supported environment variables without hidden defaults."""
    environment = os.getenv("AEGIS_ENV", "development").strip().lower()
    if environment not in {"development", "production", "test"}:
        raise ValueError("AEGIS_ENV must be development, test, or production.")
    log_level = os.getenv("AEGIS_LOG_LEVEL", "INFO").strip().upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("AEGIS_LOG_LEVEL must be a standard logging level.")
    try:
        max_upload_mb = int(os.getenv("AEGIS_MAX_UPLOAD_MB", "25"))
    except ValueError as exc:
        raise ValueError("AEGIS_MAX_UPLOAD_MB must be an integer.") from exc
    if not 1 <= max_upload_mb <= 25:
        raise ValueError(
            "AEGIS_MAX_UPLOAD_MB must be between 1 and 25 to match the parser and server limits."
        )
    configured_dir = Path(os.getenv("AEGIS_DATA_DIR", str(PROJECT_ROOT / "data" / "runtime")))
    data_dir = configured_dir.expanduser().resolve()
    password = os.getenv("AEGIS_ACCESS_PASSWORD")
    if environment == "production" and (not password or len(password) < 16):
        raise ValueError("Production requires AEGIS_ACCESS_PASSWORD with at least 16 characters.")
    return Settings(environment, log_level, data_dir, max_upload_mb, password)
