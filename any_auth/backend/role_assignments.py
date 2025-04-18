import logging
import typing

import fastapi

from any_auth.backend._base import BaseCollection
from any_auth.types.role_assignment import RoleAssignment, RoleAssignmentCreate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class RoleAssignments(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "role_assignments"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_role_assignments)

    def create(
        self,
        role_assignment_create: RoleAssignmentCreate,
        *,
        exists_ok: bool = True,
    ) -> RoleAssignment:
        doc = self.collection.find_one(
            {
                "user_id": role_assignment_create.target_id,
                "role_id": role_assignment_create.role_id,
                "resource_id": role_assignment_create.resource_id,
            }
        )
        if doc:
            logger.debug(f"Role assignment already exists: {doc}")
            if exists_ok:
                _record = RoleAssignment.model_validate(doc)
                _record._id = str(doc["_id"])
                return _record
            else:
                raise fastapi.HTTPException(
                    status_code=409, detail="Role assignment already exists."
                )

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

    def retrieve_by_target_id(
        self,
        target_id: typing.Text,
        *,
        resource_id: typing.Text,
    ) -> typing.List[RoleAssignment]:
        hard_limit = 500
        query = {"target_id": target_id, "resource_id": resource_id}
        _docs = list(self.collection.find(query).limit(hard_limit))
        role_assignments = [RoleAssignment.model_validate(doc) for doc in _docs]

        return role_assignments

    def retrieve_by_member_id(
        self,
        member_id: typing.Text,
        *,
        type: typing.Literal["organization", "project"],
        resource_id: typing.Text,
    ) -> typing.List[RoleAssignment]:
        if type == "organization":
            member = self._client.organization_members.retrieve(member_id)
            if member and member.organization_id != resource_id:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail="Member not found",
                )
        elif type == "project":
            member = self._client.project_members.retrieve(member_id)
            if member and member.project_id != resource_id:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail="Member not found",
                )
        else:
            raise ValueError(f"Invalid type: {type}")

        if not member:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="Member not found",
            )

        target_id = member.user_id

        return self.retrieve_by_target_id(target_id, resource_id=resource_id)

    def retrieve_by_role_id(
        self,
        role_id: typing.Text,
        *,
        resource_id: typing.Text | None = None,
    ) -> typing.List[RoleAssignment]:
        query = {"role_id": role_id}
        if resource_id:
            query["resource_id"] = resource_id
        _docs = list(self.collection.find(query))
        return [RoleAssignment.model_validate(doc) for doc in _docs]

    def assign_role(
        self,
        target_id: typing.Text,
        role_id: typing.Text,
        resource_id: typing.Text,
        *,
        exists_ok: bool = True,
    ) -> RoleAssignment:
        assignment_create = RoleAssignmentCreate(
            target_id=target_id,
            role_id=role_id,
            resource_id=resource_id,
        )
        assignment = self.create(assignment_create, exists_ok=exists_ok)

        return assignment

    def delete(self, id: typing.Text) -> None:
        _role_assignment = self.retrieve(id)

        if _role_assignment:
            self.collection.delete_one({"id": id})
