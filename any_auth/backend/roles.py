import logging
import typing

import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.role import Role
from any_auth.types.role_assignment import RoleAssignment

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Roles:
    def __init__(self, client):
        self._client: typing.Final["BackendClient"] = client
        self.roles_collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_roles
        )
        self.roles_collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.roles_collection_name]
        )
        self.role_assignments_collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_role_assignments
        )
        self.role_assignments_collection: typing.Final[
            pymongo.collection.Collection
        ] = self._client.database[self.role_assignments_collection_name]

    def create_role(self, role: Role) -> Role:
        self.roles_collection.insert_one(role.to_doc())
        return role

    def create_user_role_assignment(
        self,
        user_id: typing.Text,
        role_id: typing.Text,
        project_id: typing.Text,
        resource_id: typing.Text | None = None,
    ) -> RoleAssignment:
        assignment = RoleAssignment(
            user_id=user_id,
            role_id=role_id,
            project_id=project_id,
            resource_id=resource_id,
        )
        assignment = self.assign_role(assignment)
        return assignment

    def assign_role(self, assignment: RoleAssignment) -> RoleAssignment:
        result = self.role_assignments_collection.insert_one(assignment.to_doc())
        assignment._id = str(result.inserted_id)
        return assignment

    def get_role(self, role_id: typing.Text) -> typing.Optional[Role]:
        role_data = self.roles_collection.find_one({"id": role_id})
        if role_data:
            role = Role.model_validate(role_data)
            role._id = str(role_data["_id"])
            return role
        return None

    def get_roles(self, role_ids: typing.List[typing.Text]) -> typing.List[Role]:
        if not role_ids:
            logger.warning("No role IDs provided")
            return []
        roles = list(self.roles_collection.find({"id": {"$in": role_ids}}))
        return [Role.model_validate(role) for role in roles]

    def get_user_role_assignments(
        self,
        user_id: typing.Text,
        project_id: typing.Text,
        resource_id: typing.Text | None = None,
    ) -> typing.List[RoleAssignment]:
        query = {"user_id": user_id, "project_id": project_id}
        if resource_id:
            query["resource_id"] = resource_id
        _docs = list(self.role_assignments_collection.find(query))
        return [RoleAssignment.model_validate(doc) for doc in _docs]

    def get_user_roles(
        self,
        user_id: typing.Text,
        project_id: typing.Text,
        resource_id: typing.Text | None = None,
    ) -> typing.List[Role]:
        assignments = self.get_user_role_assignments(user_id, project_id, resource_id)
        roles = self.get_roles([assignment.role_id for assignment in assignments])
        return roles
