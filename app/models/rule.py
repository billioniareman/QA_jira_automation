from datetime import datetime
from app.extensions import db

class Rule(db.Model):
    __tablename__ = 'rules'

    id = db.Column(db.Integer, primary_key=True)
    rule_text = db.Column(db.Text, nullable=False)
    rule_type = db.Column(db.String(50), nullable=False)  # validation/business
    source_type = db.Column(db.String(50), nullable=False)  # jira/frontend
    source_ref = db.Column(db.String(255), nullable=True)  # jira_key or file path
    verification_status = db.Column(db.String(50), default='candidate')  # candidate/verified
    confidence = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
