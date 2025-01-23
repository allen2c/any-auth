import contextlib
import logging

import fastapi

from any_auth.config import Settings

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    logger.debug("Starting lifespan")
    yield
    logger.debug("Ending lifespan")


def build_app(settings: Settings) -> fastapi.FastAPI:
    app = fastapi.FastAPI(lifespan=lifespan)

    # Set state
    app.state.settings = settings
    return app
