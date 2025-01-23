import logging
import typing

import diskcache
import fastapi
import redis

from any_auth.backend import BackendClient
from any_auth.config import Settings

logger = logging.getLogger(__name__)


def set_status(app: fastapi.FastAPI, status: typing.Literal["ok", "error", "starting"]):
    app.state.status = status


def set_settings(app: fastapi.FastAPI, settings: Settings):
    app.state.settings = settings


def set_backend_client(app: fastapi.FastAPI, backend_client: BackendClient):
    app.state.backend_client = backend_client


def set_cache(app: fastapi.FastAPI, cache: diskcache.Cache | redis.Redis):
    app.state.cache = cache


async def depends_status(
    request: fastapi.Request,
) -> typing.Literal["ok", "error", "starting"]:
    status: typing.Literal["ok", "error", "starting"] | None = getattr(
        request.app.state, "status", None
    )
    if not status:
        raise ValueError("Application state 'status' is not set")

    return status


async def depends_settings(request: fastapi.Request) -> Settings:
    settings: Settings | None = getattr(request.app.state, "settings", None)
    if not settings:
        raise ValueError("Application state 'settings' is not set")

    return settings


async def depends_backend_client(request: fastapi.Request) -> BackendClient:
    backend_client: BackendClient | None = getattr(
        request.app.state, "backend_client", None
    )

    if not backend_client:
        raise ValueError("Application state 'backend_client' is not set")

    return backend_client


async def depends_cache(request: fastapi.Request) -> diskcache.Cache | redis.Redis:
    cache: diskcache.Cache | redis.Redis | None = getattr(
        request.app.state, "cache", None
    )
    if not cache:
        raise ValueError("Application state 'cache' is not set")

    return cache
