"""Validate deployment settings and replace this process with Streamlit safely."""

from __future__ import annotations

import os
import re
import sys


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
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]


def main() -> None:
    try:
        command = build_command()
    except ValueError as exc:
        print(f"Invalid container configuration: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
