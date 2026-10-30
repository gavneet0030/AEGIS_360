"""Validate deployment settings and replace this process with Streamlit safely."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path


def build_command(environment: dict[str, str] | None = None) -> list[str]:
    env = os.environ if environment is None else environment
    port = env.get("PORT", "8501")
    upload_mb = env.get("AEGIS_MAX_UPLOAD_MB", "25")
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535:
        raise ValueError("PORT must be an integer between 1 and 65535.")
    if not re.fullmatch(r"[0-9]{1,2}", upload_mb) or not 1 <= int(upload_mb) <= 25:
        raise ValueError("AEGIS_MAX_UPLOAD_MB must be an integer between 1 and 25.")
    return [
        "streamlit",
        "run",
        "src/aegis360/dashboard.py",
        "--server.address=0.0.0.0",
        f"--server.port={port}",
        f"--server.maxUploadSize={upload_mb}",
        "--global.developmentMode=false",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]


def provision_streamlit_secrets(environment: dict[str, str] | None = None) -> None:
    """Copy an optional mounted secret file into Streamlit's user-level secrets path."""
    env = os.environ if environment is None else environment
    source = env.get("AEGIS_STREAMLIT_SECRETS_FILE")
    if not source:
        return
    source_path = Path(source)
    if not source_path.is_file():
        raise ValueError("AEGIS_STREAMLIT_SECRETS_FILE does not reference a readable file.")
    home = Path(env.get("HOME", "/tmp"))
    destination = home / ".streamlit" / "secrets.toml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)
    destination.chmod(0o600)


def main() -> None:
    try:
        provision_streamlit_secrets()
        command = build_command()
    except (OSError, ValueError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"Invalid container configuration: {message}", file=sys.stderr)
        raise SystemExit(2) from exc
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
