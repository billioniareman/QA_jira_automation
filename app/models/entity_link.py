from app.extensions import db

class EntityLink(db.Model):
    __tablename__ = 'entity_links'

    id = db.Column(db.Integer, primary_key=True)
    from_type = db.Column(db.String(50), nullable=False)  # story/rule/frontend_signal
    from_id = db.Column(db.Integer, nullable=False)
    relation = db.Column(db.String(50), nullable=False)  # has_rule, derived_from
    to_type = db.Column(db.String(50), nullable=False)
    to_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'from_type': self.from_type,
            'from_id': self.from_id,
            'relation': self.relation,
            'to_type': self.to_type,
            'to_id': self.to_id
        }
