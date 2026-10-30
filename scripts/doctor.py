"""Check runtime configuration and writable local metadata storage."""

from __future__ import annotations

import importlib.metadata
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aegis360.settings import PROJECT_ROOT, load_settings  # noqa: E402


def main() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"FAIL configuration: {exc}")
        return 1

    print(f"Python: {sys.version.split()[0]}")
    for distribution in ("streamlit", "pandas", "numpy", "plotly", "openpyxl"):
        try:
            print(f"OK {distribution}: {importlib.metadata.version(distribution)}")
        except importlib.metadata.PackageNotFoundError:
            print(f"FAIL missing dependency: {distribution}")
            return 1
    if settings.auth_mode == "oidc":
        try:
            print(f"OK Authlib: {importlib.metadata.version('Authlib')}")
        except importlib.metadata.PackageNotFoundError:
            print("FAIL OIDC mode requires the optional auth extra (Authlib)")
            return 1
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=settings.data_dir, prefix="aegis-doctor-", delete=True
        ):
            pass
        with sqlite3.connect(settings.database_path, timeout=5) as connection:
            check = connection.execute("PRAGMA quick_check").fetchone()
            if check != ("ok",):
                raise sqlite3.DatabaseError("SQLite quick_check did not return ok")
        print(f"OK writable metadata directory: {settings.data_dir}")
    except (OSError, sqlite3.Error) as exc:
        print(f"FAIL metadata storage: {type(exc).__name__}")
        return 1
    sample = PROJECT_ROOT / "data" / "samples" / "monthly_business_performance.csv"
    if not sample.is_file():
        print("FAIL bundled sample data is missing")
        return 1
    print(f"Upload cap: {settings.max_upload_mb} MB")
    print(f"Environment: {settings.environment}")
    print("AI provider: disabled (no key required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
