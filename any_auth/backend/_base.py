import logging
import typing

import pymongo
import pymongo.collection
import pymongo.database
import pymongo.errors

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient
    from any_auth.backend.settings import BackendIndexConfig

logger = logging.getLogger(__name__)


class BaseCollection:
    def __init__(self, client: "BackendClient"):
        self._client: typing.Final["BackendClient"] = client

    @property
    def client(self):
        return self._client

    @property
    def settings(self):
        return self.client.settings

    @property
    def database(self):
        return self.client.database

    @property
    def database_name(self):
        return self.settings.database

    @property
    def collection_name(self):
        raise NotImplementedError("Subclasses must implement this property")

    @property
    def collection(self):
        return self.client.database[self.collection_name]

    def create_indexes(
        self,
        index_configs: typing.List["BackendIndexConfig"],
        *arg,
        **kwargs,
    ):
        created_indexes = self.collection.create_indexes(
            [
                pymongo.IndexModel(
                    [(key.field, key.direction) for key in index_config.keys],
                    name=index_config.name,
                    unique=index_config.unique,
                )
                for index_config in index_configs
            ]
        )
        logger.info(
            f"Created collection '{self.collection_name}' indexes: {created_indexes}"
        )
