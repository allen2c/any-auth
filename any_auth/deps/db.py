import logging

import fastapi
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from any_auth.config import Settings
from any_auth.deps.settings import depends_settings

logger = logging.getLogger(__name__)


async def depends_db(
    request: fastapi.Request, settings: Settings = fastapi.Depends(depends_settings)
) -> MongoClient:
    db: MongoClient | None = getattr(request.state, "db", None)

    # If db is already set, return it
    if db:
        return db

    db = MongoClient(
        settings.DATABASE_URL.get_secret_value(), server_api=ServerApi("1")
    )
    request.state.db = db
    logger.info("Connected to the database")
    return db
