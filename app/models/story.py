from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Story(Base):
    __tablename__ = 'stories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jira_key: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    feature: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'jira_key': self.jira_key,
            'title': self.title,
            'description': self.description,
            'acceptance_criteria': self.acceptance_criteria,
            'module': self.module,
            'feature': self.feature,
            'status': self.status,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_indexed': self.is_indexed,
            'last_indexed_at': self.last_indexed_at.isoformat() if self.last_indexed_at else None,
        }
