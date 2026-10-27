import pytest

from gia import config


@pytest.fixture(autouse=True)
def _diagnostics_in_tmp(monkeypatch, tmp_path):
    """Tests never write withheld-answer diagnostics into the project folder."""
    monkeypatch.setattr(config, "DEFAULT_DIAGNOSTICS_DIR", tmp_path / "diagnostics")
