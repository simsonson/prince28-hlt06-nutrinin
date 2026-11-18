"""App factory: build a fully wired FastAPI app from settings."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from nutrinin.api.errors import register_error_handlers
from nutrinin.api.middleware import request_context
from nutrinin.api.routes import documents, health
from nutrinin.config import Settings, get_settings
from nutrinin.db.session import make_engine, make_sessionmaker
from nutrinin.logging_setup import setup_logging

logger = logging.getLogger("nutrinin")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    engine = make_engine(settings)  # no connection is opened yet

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("starting", extra={"status": settings.app_env})
        yield
        await engine.dispose()  # close every pooled connection on shutdown

    app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)

    app.middleware("http")(request_context)
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    app.include_router(health.router)
    app.include_router(v1)
    return app
