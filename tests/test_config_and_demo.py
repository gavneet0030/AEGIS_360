import hashlib

import pytest

from aegis360.settings import load_settings
from scripts.generate_demo_data import write_demo_data
from scripts.container_entrypoint import build_command


def test_demo_data_generation_is_reproducible(tmp_path):
    destination = tmp_path / "demo.csv"
    assert write_demo_data(destination) == 72
    first_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert write_demo_data(destination) == 72
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == first_hash


def test_settings_validate_upload_limits_and_production_gate(monkeypatch, tmp_path):
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


def test_container_entrypoint_uses_exec_arguments_and_rejects_shell_input():
    command = build_command({"PORT": "10000", "AEGIS_MAX_UPLOAD_MB": "10"})
    assert "--server.port=10000" in command
    assert "--server.maxUploadSize=10" in command
    with pytest.raises(ValueError, match="PORT"):
        build_command({"PORT": "8501;echo bad", "AEGIS_MAX_UPLOAD_MB": "25"})
    with pytest.raises(ValueError, match="AEGIS_MAX_UPLOAD_MB"):
        build_command({"PORT": "8501", "AEGIS_MAX_UPLOAD_MB": "999"})
