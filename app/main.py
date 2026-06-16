"""FastAPI receiver service entry point."""

import logging

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.webhooks.phoneburner import router as phoneburner_router
from app.api.webhooks.ringcentral import router as ringcentral_router
from app.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the receiver FastAPI app."""

    app = FastAPI(title="Call Intelligence Receiver", version="0.1.0")
    app.include_router(health_router)
    app.include_router(phoneburner_router)
    app.include_router(ringcentral_router)

    @app.on_event("startup")
    async def log_startup_config() -> None:
        """Log a non-secret configuration summary at service startup."""

        logging.basicConfig(level=logging.INFO)
        logger.info("Receiver configuration loaded: %s", get_settings().safe_summary())

    return app


app = create_app()
