import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.db import make_sessionmaker
from app.services.idempotency import IdempotencyCache
from app.services.model_registry import load_bundle
from app.services.weather import WeatherService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Fail fast: a missing model or a checksum mismatch stops startup (backend/README.md).
        app.state.bundle = load_bundle(s)
        yield

    app = FastAPI(title="AgroSnap API", version=s.app_version, lifespan=lifespan)
    app.state.settings = s
    app.state.bundle = None
    app.state.idempotency = IdempotencyCache(s.idempotency_ttl_sec)
    app.state.inference_sem = asyncio.Semaphore(s.inference_max_concurrency)
    app.state.sessionmaker = make_sessionmaker(s.database_url)
    app.state.weather = WeatherService(s.weather_base_url, s.weather_cache_ttl_min)
    install_error_handlers(app)
    app.include_router(router, prefix=s.api_prefix)
    return app


app = create_app()
