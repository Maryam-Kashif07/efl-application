import pytest    # The test library
import config    # NEW: settings we change during tests
import database  # To build a test database

@pytest.fixture
def db_file(tmp_path):
    path = str(tmp_path / "test.db")
    database.init_db(path)
    return path

@pytest.fixture(autouse=True)                                          # NEW: runs before every test without being asked
def offline(monkeypatch):                                              # NEW: tests must never call the internet
    monkeypatch.setattr(config, "USE_LIVE_RATES", False)               # NEW: switch live rates off for the test

@pytest.fixture(autouse=True)                                          # NEW: also runs before every test
def private_folders(monkeypatch, tmp_path):                            # NEW: log and cache files go to a temporary folder
    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path / "logs"))     # NEW: an absolute path replaces the project's logs folder
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path / "cache"))