import os
import sys
import tempfile
from pathlib import Path
import pytest

# Insert src directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

DB_FILE = Path(tempfile.gettempdir()) / "cnpm_test_suite.db"
TEST_DB_URL = f"sqlite:///{DB_FILE.as_posix()}"

os.environ["TESTING"] = "True"
os.environ["POSTGREE_DATABASE_URL"] = TEST_DB_URL
os.environ["DATABASE_URI"] = TEST_DB_URL

from infrastructure.databases.base import Base
from infrastructure.databases.factory_database import FactoryDatabase
from sqlalchemy.orm import close_all_sessions

@pytest.fixture(scope="session", autouse=True)
def setup_test_suite_db():
    FactoryDatabase.reset()
    db = FactoryDatabase.get_database("POSTGREE")
    try:
        Base.metadata.create_all(db.engine)
    except Exception:
        pass
    yield
    try:
        close_all_sessions()
        db.engine.dispose()
    except Exception:
        pass
    try:
        DB_FILE.unlink(missing_ok=True)
    except Exception:
        pass
