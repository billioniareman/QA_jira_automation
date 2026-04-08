"""Tests for persistence layer (sessions, history, artifacts)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.chat import ChatThread, ChatMessage, ChatArtifact
from app.services.chat import SessionManager, HistoryManager


@pytest.fixture
def db():
    """Create an in-memory test database."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    engine.dispose()


class TestSessionManager:
    """Test session (thread) management."""

    def test_create_thread(self, db):
        """Test creating a new chat thread."""
        thread = SessionManager.create_thread(
            db=db,
            user_id="user-123",
            title="Test Thread",
        )
        
        assert thread.user_id == "user-123"
        assert thread.title == "Test Thread"
        assert thread.status == "active"
        assert thread.thread_id is not None

    def test_get_thread(self, db):
        """Test retrieving a thread by ID."""
        created = SessionManager.create_thread(db=db, user_id="user-123")
        
        retrieved = SessionManager.get_thread(db=db, thread_id=created.thread_id)
        
        assert retrieved is not None
        assert retrieved.thread_id == created.thread_id

    def test_get_thread_by_pk(self, db):
        """Test retrieving a thread by primary key."""
        created = SessionManager.create_thread(db=db, user_id="user-123")
        
        retrieved = SessionManager.get_thread_by_pk(db=db, thread_pk=created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_list_threads(self, db):
        """Test listing user threads."""
        SessionManager.create_thread(db=db, user_id="user-123", title="Thread 1")
        SessionManager.create_thread(db=db, user_id="user-123", title="Thread 2")
        SessionManager.create_thread(db=db, user_id="user-456", title="Thread 3")
        
        threads = SessionManager.list_threads(db=db, user_id="user-123")
        
        assert len(threads) == 2
        assert all(t.user_id == "user-123" for t in threads)

    def test_archive_thread(self, db):
        """Test archiving a thread."""
        thread = SessionManager.create_thread(db=db, user_id="user-123")
        
        archived = SessionManager.archive_thread(db=db, thread_id=thread.thread_id)
        
        assert archived.status == "archived"

    def test_delete_thread(self, db):
        """Test soft-deleting a thread."""
        thread = SessionManager.create_thread(db=db, user_id="user-123")
        
        success = SessionManager.delete_thread(db=db, thread_id=thread.thread_id)
        
        assert success is True
        
        deleted = SessionManager.get_thread(db=db, thread_id=thread.thread_id)
        assert deleted.status == "deleted"


class TestHistoryManager:
    """Test conversation history management."""

    @pytest.fixture
    def thread(self, db):
        """Create a test thread."""
        return SessionManager.create_thread(db=db, user_id="user-123")

    def test_add_message(self, db, thread):
        """Test adding a message to history."""
        message = HistoryManager.add_message(
            db=db,
            thread_pk=thread.id,
            sender_role="user",
            content="Hello, assistant!",
        )
        
        assert message.sender_role == "user"
        assert message.content == "Hello, assistant!"
        assert message.thread_id == thread.id

    def test_get_message(self, db, thread):
        """Test retrieving a message."""
        created = HistoryManager.add_message(
            db=db,
            thread_pk=thread.id,
            sender_role="user",
            content="Test",
        )
        
        retrieved = HistoryManager.get_message(db=db, message_id=created.message_id)
        
        assert retrieved is not None
        assert retrieved.message_id == created.message_id

    def test_get_thread_history(self, db, thread):
        """Test retrieving message history."""
        HistoryManager.add_message(db=db, thread_pk=thread.id, sender_role="user", content="Message 1")
        HistoryManager.add_message(db=db, thread_pk=thread.id, sender_role="assistant", content="Response 1")
        HistoryManager.add_message(db=db, thread_pk=thread.id, sender_role="user", content="Message 2")
        
        history = HistoryManager.get_thread_history(db=db, thread_pk=thread.id)
        
        assert len(history) == 3

    def test_store_artifact(self, db, thread):
        """Test storing an artifact."""
        artifact_data = '{"issue": "PROJ-123", "summary": "Test issue"}'
        
        artifact = HistoryManager.store_artifact(
            db=db,
            thread_pk=thread.id,
            artifact_type="jira_issue",
            data=artifact_data,
        )
        
        assert artifact.artifact_type == "jira_issue"
        assert artifact.artifact_id is not None
        assert artifact.thread_id == thread.id

    def test_get_artifact(self, db, thread):
        """Test retrieving an artifact."""
        artifact_data = '{"key": "value"}'
        
        created = HistoryManager.store_artifact(
            db=db,
            thread_pk=thread.id,
            artifact_type="test",
            data=artifact_data,
        )
        
        retrieved = HistoryManager.get_artifact(db=db, artifact_id=created.artifact_id)
        
        assert retrieved is not None
        assert retrieved.artifact_id == created.artifact_id

    def test_list_thread_artifacts(self, db, thread):
        """Test listing artifacts for a thread."""
        HistoryManager.store_artifact(
            db=db,
            thread_pk=thread.id,
            artifact_type="jira_issue",
            data='{}',
        )
        HistoryManager.store_artifact(
            db=db,
            thread_pk=thread.id,
            artifact_type="search_result",
            data='{}',
        )
        
        artifacts = HistoryManager.list_thread_artifacts(db=db, thread_pk=thread.id)
        
        assert len(artifacts) == 2

    def test_list_artifacts_by_type(self, db, thread):
        """Test filtering artifacts by type."""
        HistoryManager.store_artifact(db=db, thread_pk=thread.id, artifact_type="jira_issue", data='{}')
        HistoryManager.store_artifact(db=db, thread_pk=thread.id, artifact_type="jira_issue", data='{}')
        HistoryManager.store_artifact(db=db, thread_pk=thread.id, artifact_type="search_result", data='{}')
        
        jira_artifacts = HistoryManager.list_thread_artifacts(
            db=db,
            thread_pk=thread.id,
            artifact_type="jira_issue",
        )
        
        assert len(jira_artifacts) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
