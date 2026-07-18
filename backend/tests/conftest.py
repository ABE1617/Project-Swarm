"""Test configuration: point the app at a throwaway SQLite DB before any app import."""

import os
from pathlib import Path

_TEST_DB = Path(__file__).parent / ".test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["SWARM_DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
