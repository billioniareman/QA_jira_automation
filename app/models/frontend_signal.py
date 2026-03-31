from app.extensions import db

class FrontendSignal(db.Model):
    __tablename__ = 'frontend_signals'

    id = db.Column(db.Integer, primary_key=True)
    repo = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    artifact_type = db.Column(db.String(100), nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)
    route = db.Column(db.String(255), nullable=True)
    component = db.Column(db.String(255), nullable=True)
    commit_sha = db.Column(db.String(100), nullable=True)
