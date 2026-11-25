import pytest
import config
import database

@pytest.fixture
def db_file(tmp_path):
    path = str(tmp_path / "test.db")
    database.init_db(path)
    return path

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(config, "USE_LIVE_RATES", False)

@pytest.fixture(autouse=True)
def private_folders(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path / "cache"))