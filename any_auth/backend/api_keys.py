import json
import logging
import time
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.database
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
)
from any_auth.types.pagination import Page

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class APIKeys(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "api_keys"

    def create_indexes(
        self,
        *args,
        **kwargs,
    ):
        super().create_indexes(self.settings.indexes_api_keys)
