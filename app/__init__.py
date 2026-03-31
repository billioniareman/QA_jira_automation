from flask import Flask
from config import Config
from app.extensions import db, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes.endpoints import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Import models so Alembic can discover them
    from app import models

    return app
