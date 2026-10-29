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
