import hashlib
import os

import pytest

from aegis360.settings import load_settings
from scripts.generate_demo_data import write_demo_data
from aegis360.auth import email_is_allowed
from scripts.container_entrypoint import build_command, provision_streamlit_secrets


def test_demo_data_generation_is_reproducible(tmp_path):
    destination = tmp_path / "demo.csv"
    assert write_demo_data(destination) == 72
    first_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert write_demo_data(destination) == 72
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == first_hash


def test_settings_validate_upload_limits_and_production_gate(monkeypatch, tmp_path):
    monkeypatch.delenv("AEGIS_AUTH_MODE", raising=False)
    monkeypatch.delenv("AEGIS_OIDC_ALLOWED_DOMAINS", raising=False)
    monkeypatch.delenv("AEGIS_OIDC_ALLOWED_EMAILS", raising=False)
    monkeypatch.setenv("AEGIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AEGIS_MAX_UPLOAD_MB", "10")
    settings = load_settings()
    assert settings.max_upload_mb == 10
    assert settings.database_path.parent == (tmp_path / "data").resolve()

    monkeypatch.setenv("AEGIS_ENV", "production")
    monkeypatch.delenv("AEGIS_ACCESS_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="Production requires"):
        load_settings()
    monkeypatch.setenv("AEGIS_ACCESS_PASSWORD", "x" * 20)
    assert load_settings().environment == "production"


def test_settings_reject_invalid_values(monkeypatch):
    monkeypatch.setenv("AEGIS_ENV", "staging")
    with pytest.raises(ValueError, match="AEGIS_ENV"):
        load_settings()
    monkeypatch.setenv("AEGIS_ENV", "development")
    monkeypatch.setenv("AEGIS_MAX_UPLOAD_MB", "1000")
    with pytest.raises(ValueError, match="between"):
        load_settings()


def test_oidc_settings_require_a_valid_allowlist_in_production(monkeypatch):
    monkeypatch.setenv("AEGIS_ENV", "production")
    monkeypatch.setenv("AEGIS_AUTH_MODE", "oidc")
    monkeypatch.delenv("AEGIS_ACCESS_PASSWORD", raising=False)
    monkeypatch.delenv("AEGIS_OIDC_ALLOWED_DOMAINS", raising=False)
    monkeypatch.delenv("AEGIS_OIDC_ALLOWED_EMAILS", raising=False)
    with pytest.raises(ValueError, match="requires AEGIS_OIDC_ALLOWED"):
        load_settings()

    monkeypatch.setenv("AEGIS_OIDC_ALLOWED_DOMAINS", "example.com,corp.example")
    settings = load_settings()
    assert settings.auth_mode == "oidc"
    assert settings.oidc_allowed_domains == ("example.com", "corp.example")

    monkeypatch.setenv("AEGIS_OIDC_ALLOWED_DOMAINS", "@example.com")
    with pytest.raises(ValueError, match="valid domain"):
        load_settings()


def test_oidc_email_allowlist_matches_domains_and_exact_addresses():
    domains = ("example.com",)
    emails = ("analyst@other.example",)
    assert email_is_allowed("USER@example.com", domains, ())
    assert email_is_allowed("analyst@other.example", (), emails)
    assert not email_is_allowed("outsider@other.example", domains, emails)
    assert not email_is_allowed("@example.com", domains, emails)


def test_container_entrypoint_copies_oidc_secrets_without_exposing_values(tmp_path):
    source = tmp_path / "mounted-secrets.toml"
    source.write_text("[auth]\nclient_secret = 'never-log-this'\n", encoding="utf-8")
    home = tmp_path / "home"
    provision_streamlit_secrets({"AEGIS_STREAMLIT_SECRETS_FILE": str(source), "HOME": str(home)})
    destination = home / ".streamlit" / "secrets.toml"
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    if os.name != "nt":
        assert destination.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="readable file"):
        provision_streamlit_secrets(
            {"AEGIS_STREAMLIT_SECRETS_FILE": str(tmp_path / "missing.toml"), "HOME": str(home)}
        )


def test_container_entrypoint_uses_exec_arguments_and_rejects_shell_input():
    command = build_command({"PORT": "10000", "AEGIS_MAX_UPLOAD_MB": "10"})
    assert "--server.port=10000" in command
    assert "--server.maxUploadSize=10" in command
    assert "--global.developmentMode=false" in command
    with pytest.raises(ValueError, match="PORT"):
        build_command({"PORT": "8501;echo bad", "AEGIS_MAX_UPLOAD_MB": "25"})
    with pytest.raises(ValueError, match="AEGIS_MAX_UPLOAD_MB"):
        build_command({"PORT": "8501", "AEGIS_MAX_UPLOAD_MB": "999"})
