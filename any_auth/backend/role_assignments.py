import logging
import typing

import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.role_assignment import RoleAssignment, RoleAssignmentCreate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient, BackendIndexConfig

logger = logging.getLogger(__name__)


class RoleAssignments:
    def __init__(self, client):
        self._client: typing.Final["BackendClient"] = client
        self.collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_role_assignments
        )
        self.collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.collection_name]
        )

    def create_indexes(
        self, index_configs: typing.Optional[typing.List["BackendIndexConfig"]] = None
    ):
        if index_configs is None:
            index_configs = self._client.settings.indexes_role_assignments

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
        logger.info(f"Created indexes: {created_indexes}")

    def create(self, role_assignment_create: RoleAssignmentCreate) -> RoleAssignment:
        role_assignment = role_assignment_create.to_role_assignment()
        result = self.collection.insert_one(role_assignment.to_doc())
        role_assignment._id = str(result.inserted_id)
        return role_assignment

    def retrieve(
        self,
        id: typing.Text,
    ) -> typing.Optional[RoleAssignment]:
        role_assignment_data = self.collection.find_one({"id": id})
        if role_assignment_data:
            role_assignment = RoleAssignment.model_validate(role_assignment_data)
            role_assignment._id = str(role_assignment_data["_id"])
            return role_assignment
        return None

    def retrieve_by_user_id(
        self,
        *,
        user_id: typing.Text,
        project_id: typing.Text,
        resource_id: typing.Text | None = None,
    ) -> typing.List[RoleAssignment]:
        query = {"user_id": user_id, "project_id": project_id}
        if resource_id:
            query["resource_id"] = resource_id
        _docs = list(self.collection.find(query))
        return [RoleAssignment.model_validate(doc) for doc in _docs]

    def assign_role(
        self,
        user_id: typing.Text,
        role_id: typing.Text,
        project_id: typing.Text,
        resource_id: typing.Text | None = None,
    ) -> RoleAssignment:
        assignment_create = RoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            project_id=project_id,
            resource_id=resource_id,
        )
        assignment = self.create(assignment_create)
        return assignment
