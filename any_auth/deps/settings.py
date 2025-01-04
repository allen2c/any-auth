import logging

import fastapi

from any_auth.config import Settings

logger = logging.getLogger(__name__)


async def depends_settings(request: fastapi.Request) -> Settings:
    settings: Settings | None = getattr(request.state, "settings", None)
    if settings:
        return settings

    settings = Settings()  # type: ignore
    request.state.settings = settings

    logger.info("Initialized settings")
    return settings
