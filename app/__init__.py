from fastapi import FastAPI

from config import settings
from app.routes.endpoints import api_router

def create_app():
    app = FastAPI(title=settings.APP_NAME)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Import models so Alembic can discover metadata
    from app import models  # noqa: F401

    return app
