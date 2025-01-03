import logging

import fastapi
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from any_auth.config import Settings

logger = logging.getLogger(__name__)


async def get_db(request: fastapi.Request) -> MongoClient:
    db: MongoClient | None = getattr(request.state, "db", None)

    # If db is already set, return it
    if db:
        return db

    settings: Settings | None = getattr(request.state, "settings", None)

    # If settings is already set, use it to connect to the database
    if settings:
        db = MongoClient(
            settings.DATABASE_URL.get_secret_value(), server_api=ServerApi("1")
        )
        request.state.db = db
        logger.info("Connected to the database")
        return db

    settings = Settings()  # type: ignore
    request.state.settings = settings
    logger.info("Initialized settings")

    db = MongoClient(
        settings.DATABASE_URL.get_secret_value(), server_api=ServerApi("1")
    )
    request.state.db = db
    logger.info("Connected to the database")
    return db
