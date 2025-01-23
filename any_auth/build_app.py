import asyncio
import contextlib
import logging

import fastapi
import httpx
import pymongo
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from starlette.middleware.sessions import SessionMiddleware

import any_auth.deps.app_state
from any_auth.api.auth import router as auth_router
from any_auth.api.root import router as root_router
from any_auth.backend import BackendClient, BackendSettings
from any_auth.config import Settings

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    logger.debug("Application starting lifespan")

    # Touch the backend
    async def touch_backend():
        try:
            logger.debug("Touching backend")
            backend_client: BackendClient = app.state.backend_client
            await asyncio.to_thread(backend_client.touch)
            logger.debug("Touched backend")
            any_auth.deps.app_state.set_status(app, "ok")
            logger.debug("Application state set to 'ok'")
        except Exception as e:
            logger.error(f"Error touching backend: {e}")
            any_auth.deps.app_state.set_status(app, "error")
            logger.debug("Application state set to 'error'")

    await touch_backend()

    # Set health to ok
    any_auth.deps.app_state.set_status(app, "ok")

    yield

    # Close the backend client
    try:
        logger.debug("Closing backend client")
        backend_client: BackendClient = app.state.backend_client
        backend_client.close()
        logger.debug("Closed backend client")
    except Exception as e:
        logger.error(f"Error closing backend client: {e}")

    logger.debug("Application ending lifespan")


def build_app(settings: Settings) -> fastapi.FastAPI:

    app = fastapi.FastAPI(lifespan=lifespan)

    # Set state
    any_auth.deps.app_state.set_status(app, "starting")
    any_auth.deps.app_state.set_settings(app, settings)
    any_auth.deps.app_state.set_cache(app, settings.cache)
    _backend_settings = BackendSettings()
    if settings.ENVIRONMENT != "production":
        _backend_settings.database += f"_{settings.ENVIRONMENT}"
    _backend_client = BackendClient(
        pymongo.MongoClient(str(httpx.URL(settings.DATABASE_URL.get_secret_value()))),
        _backend_settings,
    )
    any_auth.deps.app_state.set_backend_client(app, _backend_client)

    # Add middleware
    app.add_middleware(
        SessionMiddleware, secret_key=settings.JWT_SECRET_KEY.get_secret_value()
    )

    # Add OAuth
    if settings.is_google_oauth_configured():
        assert settings.GOOGLE_CLIENT_ID is not None
        assert settings.GOOGLE_CLIENT_SECRET is not None
        assert settings.GOOGLE_REDIRECT_URI is not None
        starlette_config = StarletteConfig(
            environ={
                "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID.get_secret_value(),
                "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),  # noqa: E501
                "GOOGLE_REDIRECT_URI": settings.GOOGLE_REDIRECT_URI.get_secret_value(),
            }
        )
        oauth = OAuth(starlette_config)
        oauth.register(
            name="google",
            client_id=settings.GOOGLE_CLIENT_ID.get_secret_value(),
            client_secret=settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            access_token_url="https://oauth2.googleapis.com/token",
            authorize_url="https://accounts.google.com/o/oauth2/auth",
            api_base_url="https://www.googleapis.com/oauth2/v1/",
            client_kwargs={"scope": "openid email profile"},
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",  # noqa: E501
        )
        app.state.starlette_config = starlette_config
        app.state.oauth = oauth

    # Add routes
    app.include_router(root_router)
    app.include_router(auth_router)

    return app
