from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

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
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
