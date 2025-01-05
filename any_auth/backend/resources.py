import typing

import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.resource import Resource

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient


class Resources:
    def __init__(self, client: "BackendClient"):
        self._client: typing.Final["BackendClient"] = client
        self.collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_resources
        )
        self.collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.collection_name]
        )

    def create(self, resource: Resource) -> Resource:
        self.collection.insert_one(resource.to_doc())
        return resource

    def retrieve(self, resource_id: typing.Text) -> typing.Optional[Resource]:
        resource_data = self.collection.find_one({"id": resource_id})
        if resource_data:
            resource = Resource.model_validate(resource_data)
            resource._id = resource_data["_id"]
            return resource
        return None
