"""
Pytest configuration — create database tables before tests run.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all database tables in the test database before any tests run."""
    from app.db.session import engine
    from app.db.base import Base
    import app.models.complaint  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    # Optionally clean up
    # Base.metadata.drop_all(bind=engine)
