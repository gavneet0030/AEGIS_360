from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_renders_all_core_controls(monkeypatch, tmp_path):
    monkeypatch.setenv("AEGIS_ENV", "test")
    monkeypatch.setenv("AEGIS_DATA_DIR", str(tmp_path / "runtime"))
    app = AppTest.from_file(
        str(PROJECT_ROOT / "src" / "aegis360" / "dashboard.py"), default_timeout=60
    ).run()
    assert not app.exception
    assert len(app.selectbox) >= 3
    assert len(app.metric) >= 4
    app.button[1].click().run()
    assert not app.exception
    assert any("Workbook generated" in message.value for message in app.success)


def test_oidc_mode_fails_closed_without_provider_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("AEGIS_ENV", "test")
    monkeypatch.setenv("AEGIS_AUTH_MODE", "oidc")
    monkeypatch.setenv("AEGIS_OIDC_ALLOWED_DOMAINS", "example.com")
    monkeypatch.setenv("AEGIS_DATA_DIR", str(tmp_path / "runtime"))
    app = AppTest.from_file(
        str(PROJECT_ROOT / "src" / "aegis360" / "dashboard.py"), default_timeout=60
    ).run()
    assert not app.exception
    assert any("authentication settings are missing" in error.value for error in app.error)
