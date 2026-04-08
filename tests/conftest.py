"""Pytest configuration and fixtures for the test suite."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DEBUG'] = 'true'
os.environ['LANGFUSE_ENABLED'] = 'false'


@pytest.fixture(scope='session')
def test_db_engine():
    """Create a test database engine (in-memory SQLite)."""
    engine = create_engine('sqlite:///:memory:')
    
    # Import and create all tables
    from app.db import Base
    Base.metadata.create_all(engine)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope='function')
def db_session(test_db_engine):
    """Create a new database session for each test."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def mock_azure_services(monkeypatch):
    """Mock Azure services for tests."""
    # Mock LLM to prevent actual API calls
    def mock_get_llm():
        from unittest.mock import MagicMock
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value="mocked response")
        return mock_llm
    
    # Patch the LLM initialization
    monkeypatch.setenv('AZURE_OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com')


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (for pytest-asyncio)"
    )
