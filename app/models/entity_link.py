from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

class EntityLink(Base):
    __tablename__ = 'entity_links'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_type: Mapped[str] = mapped_column(String(50), nullable=False)  # story/rule/frontend_signal
    from_id: Mapped[int] = mapped_column(Integer, nullable=False)
    relation: Mapped[str] = mapped_column(String(50), nullable=False)  # has_rule, derived_from
    to_type: Mapped[str] = mapped_column(String(50), nullable=False)
    to_id: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'from_type': self.from_type,
            'from_id': self.from_id,
            'relation': self.relation,
            'to_type': self.to_type,
            'to_id': self.to_id
        }
