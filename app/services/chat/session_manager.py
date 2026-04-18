"""Session and thread management for chat."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select, desc

from app.models.chat import ChatThread, ChatMessage


class SessionManager:
    """Manages chat session (thread) lifecycle."""

    @staticmethod
    def create_thread(
        db: DBSession,
        user_id: str,
        title: Optional[str] = None,
    ) -> ChatThread:
        """
        Create a new chat thread (session).
        
        Args:
            db: Database session
            user_id: External user identifier
            title: Optional thread title
            
        Returns:
            ChatThread instance
        """
        thread_id = str(uuid.uuid4())
        thread = ChatThread(
            thread_id=thread_id,
            user_id=user_id,
            title=title or f'Chat {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}',
            status='active',
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
        return thread

    @staticmethod
    def get_thread(db: DBSession, thread_id: str) -> Optional[ChatThread]:
        """Retrieve a chat thread by ID."""
        return db.execute(
            select(ChatThread).where(ChatThread.thread_id == thread_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_thread_by_pk(db: DBSession, thread_pk: int) -> Optional[ChatThread]:
        """Retrieve a chat thread by primary key."""
        return db.execute(
            select(ChatThread).where(ChatThread.id == thread_pk)
        ).scalar_one_or_none()

    @staticmethod
    def list_threads(
        db: DBSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ChatThread]:
        """
        List all threads for a user.
        
        Args:
            db: Database session
            user_id: External user identifier
            limit: Number of results to return
            offset: Offset for pagination
            
        Returns:
            List of ChatThread instances
        """
        return db.execute(
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .where(ChatThread.status == 'active')
            .order_by(desc(ChatThread.updated_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()

    @staticmethod
    def archive_thread(db: DBSession, thread_id: str) -> ChatThread:
        """Archive a chat thread."""
        thread = SessionManager.get_thread(db, thread_id)
        if thread:
            thread.status = 'archived'
            thread.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(thread)
        return thread

    @staticmethod
    def delete_thread(db: DBSession, thread_id: str) -> bool:
        """Soft-delete a chat thread."""
        thread = SessionManager.get_thread(db, thread_id)
        if thread:
            thread.status = 'deleted'
            thread.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False
