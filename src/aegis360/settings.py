"""Validated environment configuration for local and container deployment."""

from __future__ import annotations

import os
import re
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
    auth_mode: str
    oidc_allowed_domains: tuple[str, ...]
    oidc_allowed_emails: tuple[str, ...]

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
    auth_mode = os.getenv("AEGIS_AUTH_MODE", "password").strip().lower()
    if auth_mode not in {"password", "oidc"}:
        raise ValueError("AEGIS_AUTH_MODE must be password or oidc.")
    allowed_domains = tuple(
        item.strip().casefold()
        for item in os.getenv("AEGIS_OIDC_ALLOWED_DOMAINS", "").split(",")
        if item.strip()
    )
    allowed_emails = tuple(
        item.strip().casefold()
        for item in os.getenv("AEGIS_OIDC_ALLOWED_EMAILS", "").split(",")
        if item.strip()
    )
    domain_pattern = re.compile(
        r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*"
    )
    if any(not domain_pattern.fullmatch(item) for item in allowed_domains):
        raise ValueError("AEGIS_OIDC_ALLOWED_DOMAINS must contain valid domain names only.")
    if any(
        item.count("@") != 1 or " " in item or not all(item.rsplit("@", 1))
        for item in allowed_emails
    ):
        raise ValueError("AEGIS_OIDC_ALLOWED_EMAILS must contain complete email addresses.")
    if (
        environment == "production"
        and auth_mode == "password"
        and (not password or len(password) < 16)
    ):
        raise ValueError("Production requires AEGIS_ACCESS_PASSWORD with at least 16 characters.")
    if (
        environment == "production"
        and auth_mode == "oidc"
        and not (allowed_domains or allowed_emails)
    ):
        raise ValueError(
            "Production OIDC requires AEGIS_OIDC_ALLOWED_DOMAINS or AEGIS_OIDC_ALLOWED_EMAILS."
        )
    return Settings(
        environment,
        log_level,
        data_dir,
        max_upload_mb,
        password,
        auth_mode,
        allowed_domains,
        allowed_emails,
    )
