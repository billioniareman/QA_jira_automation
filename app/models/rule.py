from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

class Rule(Base):
    __tablename__ = 'rules'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # validation/business
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # jira/frontend
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # jira_key or file path
    verification_status: Mapped[str] = mapped_column(String(50), default='candidate')  # candidate/verified
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'rule_text': self.rule_text,
            'rule_type': self.rule_type,
            'source_type': self.source_type,
            'source_ref': self.source_ref,
            'verification_status': self.verification_status,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
