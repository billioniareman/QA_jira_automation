"""Chat-related SQLAlchemy models."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatThread(Base):
    """Represents a conversation thread (session)."""

    __tablename__ = 'chat_threads'

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(String(255), index=True, nullable=False)  # External user ID
    title = Column(String(255), nullable=True)  # Auto-generated or user-provided
    status = Column(String(50), default='active', nullable=False)  # active, archived, deleted
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    metadata_json = Column(JSON, nullable=True)  # Additional thread metadata

    # Relationships
    messages = relationship('ChatMessage', back_populates='thread', cascade='all, delete-orphan')
    checkpoints = relationship('ChatCheckpoint', back_populates='thread', cascade='all, delete-orphan')
    artifacts = relationship('ChatArtifact', back_populates='thread', cascade='all, delete-orphan')


class ChatMessage(Base):
    """Represents a message in a conversation thread."""

    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey('chat_threads.id'), nullable=False, index=True)
    message_id = Column(String(255), unique=True, index=True, nullable=False)  # UUID
    sender_role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    tokens_in = Column(Integer, nullable=True)  # Token count for LLM input
    tokens_out = Column(Integer, nullable=True)  # Token count for LLM output
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    metadata_json = Column(JSON, nullable=True)  # Tool calls, routing info, etc.

    # Relationships
    thread = relationship('ChatThread', back_populates='messages')


class ChatArtifact(Base):
    """Stores large outputs (Jira responses, search results) referenced by messages."""

    __tablename__ = 'chat_artifacts'

    id = Column(Integer, primary_key=True, index=True)
    artifact_id = Column(String(255), unique=True, index=True, nullable=False)  # UUID
    thread_id = Column(Integer, ForeignKey('chat_threads.id'), nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False)  # 'jira_issue', 'jira_search', etc.
    size_bytes = Column(Integer, nullable=False)
    compressed = Column(Boolean, default=False)
    data = Column(Text, nullable=False)  # JSON or gzipped data
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    metadata_json = Column(JSON, nullable=True)  # Version, source, etc.

    # Relationships
    thread = relationship('ChatThread', back_populates='artifacts')


class ChatCheckpoint(Base):
    """Stores LangGraph execution state for recovery and resumption."""

    __tablename__ = 'chat_checkpoints'

    id = Column(Integer, primary_key=True, index=True)
    checkpoint_id = Column(String(255), unique=True, index=True, nullable=False)  # UUID
    thread_id = Column(Integer, ForeignKey('chat_threads.id'), nullable=False, index=True)
    message_id = Column(String(255), nullable=False)  # Associated message
    checkpoint_index = Column(Integer, nullable=False)  # Step in execution
    graph_state_json = Column(JSON, nullable=False)  # Serialized LangGraph state
    status = Column(String(50), default='pending', nullable=False)  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    thread = relationship('ChatThread', back_populates='checkpoints')
