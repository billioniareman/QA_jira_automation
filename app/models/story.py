from datetime import datetime
from app.extensions import db

class Story(db.Model):
    __tablename__ = 'stories'

    id = db.Column(db.Integer, primary_key=True)
    jira_key = db.Column(db.String(50), unique=True, index=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    acceptance_criteria = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(100), index=True, nullable=True)
    feature = db.Column(db.String(100), index=True, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
