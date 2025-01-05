import logging
import typing

import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.organization import Organization

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Organizations:
    def __init__(self, client: "BackendClient"):
        self._client: typing.Final["BackendClient"] = client
        self.collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_organizations
        )
        self.collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.collection_name]
        )

    def create_organization(self, org: Organization) -> Organization:
        self.collection.insert_one(org.to_doc())
        return org

    def retrieve_organization(
        self, org_id: typing.Text
    ) -> typing.Optional[Organization]:
        org_data = self.collection.find_one({"id": org_id})
        if org_data:
            org = Organization.model_validate(org_data)
            org._id = str(org_data["_id"])
            return org
        return None

    def list_organizations(self, limit: int = 100) -> typing.List[Organization]:
        orgs = list(self.collection.find().limit(limit))
        return [Organization.model_validate(org) for org in orgs]
