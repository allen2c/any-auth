import logging
import typing

import fastapi
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
        logger.info(
            f"Created collection '{self.collection_name}' indexes: {created_indexes}"
        )

    def create(
        self,
        role_assignment_create: RoleAssignmentCreate,
        *,
        exists_ok: bool = True,
    ) -> RoleAssignment:
        doc = self.collection.find_one(
            {
                "user_id": role_assignment_create.user_id,
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

        # Delete cache
        self._client.cache.delete(f"role_assignment:{role_assignment.id}")

        return role_assignment

    def retrieve(
        self,
        id: typing.Text,
    ) -> typing.Optional[RoleAssignment]:
        # Get from cache
        cached_role_assignment = self._client.cache.get(f"role_assignment:{id}")
        if cached_role_assignment:
            return RoleAssignment.model_validate_json(
                cached_role_assignment  # type: ignore
            )

        role_assignment_data = self.collection.find_one({"id": id})
        if role_assignment_data:
            role_assignment = RoleAssignment.model_validate(role_assignment_data)
            role_assignment._id = str(role_assignment_data["_id"])

            # Cache
            self._client.cache.set(
                f"role_assignment:{id}",
                role_assignment.model_dump_json(),
                self._client.cache_ttl,
            )

            return role_assignment
        return None

    def retrieve_by_user_id(
        self,
        user_id: typing.Text,
        *,
        resource_id: typing.Text,
    ) -> typing.List[RoleAssignment]:
        hard_limit = 500
        query = {"user_id": user_id, "resource_id": resource_id}
        _docs = list(self.collection.find(query).limit(hard_limit))
        return [RoleAssignment.model_validate(doc) for doc in _docs]

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

        user_id = member.user_id

        return self.retrieve_by_user_id(user_id, resource_id=resource_id)

    def assign_role(
        self,
        user_id: typing.Text,
        role_id: typing.Text,
        resource_id: typing.Text,
        *,
        exists_ok: bool = True,
    ) -> RoleAssignment:
        assignment_create = RoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            resource_id=resource_id,
        )
        assignment = self.create(assignment_create, exists_ok=exists_ok)

        # Delete cache
        self._client.cache.delete(f"role_assignment:{assignment.id}")

        return assignment

    def delete(self, id: typing.Text) -> None:
        self.collection.delete_one({"id": id})

        # Delete cache
        self._client.cache.delete(f"role_assignment:{id}")
