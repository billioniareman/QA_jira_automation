from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the FastAPI application."""
    # -- startup --
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    # Import models so SQLAlchemy metadata is populated
    from app import models  # noqa: F401
    yield
    # -- shutdown --
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    from app.routes.endpoints import api_router
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app
