import logging
import typing

import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.role import Role, RoleCreate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Roles:
    def __init__(self, client):
        self._client: typing.Final["BackendClient"] = client
        self.collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_roles
        )
        self.collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.collection_name]
        )

    def create(self, role_create: RoleCreate) -> Role:
        role = role_create.to_role()
        result = self.collection.insert_one(role.to_doc())
        role._id = str(result.inserted_id)
        return role

    def retrieve(self, id: typing.Text) -> typing.Optional[Role]:
        role_data = self.collection.find_one({"id": id})
        if role_data:
            role = Role.model_validate(role_data)
            role._id = str(role_data["_id"])
            return role
        return None

    def retrieve_by_ids(self, ids: typing.List[typing.Text]) -> typing.List[Role]:
        if not ids:
            logger.warning("No role IDs provided")
            return []
        roles = list(self.collection.find({"id": {"$in": ids}}))
        return [Role.model_validate(role) for role in roles]

    def retrieve_by_user_id(
        self,
        user_id: typing.Text,
        project_id: typing.Text,
        resource_id: typing.Text | None = None,
    ) -> typing.List[Role]:
        assignments = self._client.role_assignments.retrieve_by_user_id(
            user_id=user_id, project_id=project_id, resource_id=resource_id
        )
        roles = self.retrieve_by_ids([assignment.role_id for assignment in assignments])
        return roles
