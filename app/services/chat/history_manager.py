"""Conversation history management for chat."""

import uuid
import gzip
import json
from datetime import datetime
from typing import Optional, List, Any, Dict

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select, desc

from app.models.chat import ChatMessage, ChatArtifact
from config import settings


class HistoryManager:
    """Manages conversation history and artifacts."""

    @staticmethod
    def add_message(
        db: DBSession,
        thread_pk: int,
        sender_role: str,
        content: str,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """
        Add a message to the conversation history.
        
        Args:
            db: Database session
            thread_pk: Primary key of the thread
            sender_role: 'user', 'assistant', or 'system'
            content: Message text
            tokens_in: Token count for LLM input
            tokens_out: Token count for LLM output
            metadata: Additional metadata (tool calls, routing info, etc.)
            
        Returns:
            ChatMessage instance
        """
        message_id = str(uuid.uuid4())
        message = ChatMessage(
            thread_id=thread_pk,
            message_id=message_id,
            sender_role=sender_role,
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            metadata_json=metadata or {},
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_message(db: DBSession, message_id: str) -> Optional[ChatMessage]:
        """Retrieve a message by ID."""
        return db.execute(
            select(ChatMessage).where(ChatMessage.message_id == message_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_thread_history(
        db: DBSession,
        thread_pk: int,
        limit: Optional[int] = None,
    ) -> List[ChatMessage]:
        """
        Get message history for a thread, ordered by creation time.
        
        Args:
            db: Database session
            thread_pk: Primary key of the thread
            limit: Max messages to retrieve (defaults to CHAT_MAX_HISTORY_MESSAGES)
            
        Returns:
            List of ChatMessage instances
        """
        if limit is None:
            limit = settings.CHAT_MAX_HISTORY_MESSAGES

        return db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_pk)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        ).scalars().all()

    @staticmethod
    def store_artifact(
        db: DBSession,
        thread_pk: int,
        artifact_type: str,
        data: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatArtifact:
        """
        Store a large tool output as an artifact.
        
        Args:
            db: Database session
            thread_pk: Primary key of the thread
            artifact_type: Type of artifact ('jira_issue', 'jira_search', etc.)
            data: JSON string or serialized data
            metadata: Additional metadata
            
        Returns:
            ChatArtifact instance
        """
        artifact_id = str(uuid.uuid4())

        # Check compression
        data_bytes = data.encode('utf-8')
        compressed = False
        stored_data = data

        if settings.ARTIFACT_COMPRESSION_ENABLED and len(data_bytes) > 1024:
            try:
                compressed_data = gzip.compress(data_bytes)
                if len(compressed_data) < len(data_bytes):
                    # Compression saves space
                    stored_data = compressed_data.hex()
                    compressed = True
            except Exception:
                # Fall back to uncompressed
                pass

        size_bytes = len(stored_data.encode('utf-8'))

        # Check size limit
        if size_bytes > settings.ARTIFACT_MAX_SIZE_MB * 1024 * 1024:
            raise ValueError(
                f'Artifact exceeds max size of {settings.ARTIFACT_MAX_SIZE_MB}MB'
            )

        artifact = ChatArtifact(
            artifact_id=artifact_id,
            thread_id=thread_pk,
            artifact_type=artifact_type,
            size_bytes=size_bytes,
            compressed=compressed,
            data=stored_data,
            metadata_json=metadata or {},
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return artifact

    @staticmethod
    def get_artifact(db: DBSession, artifact_id: str) -> Optional[ChatArtifact]:
        """Retrieve an artifact by ID."""
        return db.execute(
            select(ChatArtifact).where(ChatArtifact.artifact_id == artifact_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_artifact_data(db: DBSession, artifact_id: str) -> Optional[str]:
        """
        Retrieve and decompress artifact data.
        
        Returns:
            Artifact data as string
        """
        artifact = HistoryManager.get_artifact(db, artifact_id)
        if not artifact:
            return None

        if artifact.compressed:
            try:
                compressed_bytes = bytes.fromhex(artifact.data)
                decompressed = gzip.decompress(compressed_bytes)
                return decompressed.decode('utf-8')
            except Exception as e:
                raise ValueError(f'Failed to decompress artifact: {e}')

        return artifact.data

    @staticmethod
    def list_thread_artifacts(
        db: DBSession,
        thread_pk: int,
        artifact_type: Optional[str] = None,
    ) -> List[ChatArtifact]:
        """List artifacts for a thread, optionally filtered by type."""
        query = select(ChatArtifact).where(ChatArtifact.thread_id == thread_pk)

        if artifact_type:
            query = query.where(ChatArtifact.artifact_type == artifact_type)

        return db.execute(query.order_by(desc(ChatArtifact.created_at))).scalars().all()
