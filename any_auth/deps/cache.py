import logging
import pathlib

import diskcache
import fastapi
import redis

from any_auth.config import Settings
from any_auth.deps.settings import depends_settings

logger = logging.getLogger(__name__)


async def depends_cache(
    request: fastapi.Request, settings: Settings = fastapi.Depends(depends_settings)
) -> diskcache.Cache | redis.Redis:
    cache: diskcache.Cache | redis.Redis | None = getattr(request.state, "cache", None)

    # If cache is already set, return it
    if cache:
        return cache

    # If cache is not set, create a new one
    if settings.CACHE_URL:  # Use Redis if CACHE_URL is provided
        cache = redis.Redis(settings.CACHE_URL.get_secret_value())
    else:  # Use DiskCache if CACHE_URL is not provided
        cache = diskcache.Cache(pathlib.Path("./.cache").resolve())

    request.state.cache = cache

    logger.info(f"Initialized cache: {cache}")
    return cache
