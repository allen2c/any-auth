import json
import logging
import time
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.database
import pymongo.errors

from any_auth.types.pagination import Page
from any_auth.types.role import Role, RoleCreate, RoleUpdate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient, BackendIndexConfig

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

    def create_indexes(
        self, index_configs: typing.Optional[typing.List["BackendIndexConfig"]] = None
    ):
        if index_configs is None:
            index_configs = self._client.settings.indexes_roles

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

    def retrieve_by_name(self, name: typing.Text) -> typing.Optional[Role]:
        role_data = self.collection.find_one({"name": name})
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
    ) -> typing.List[Role]:
        assignments = self._client.role_assignments.retrieve_by_user_id(
            user_id=user_id, project_id=project_id
        )
        roles = self.retrieve_by_ids([assignment.role_id for assignment in assignments])
        return roles

    def list(
        self,
        *,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[Role]:
        limit = limit or 20
        if limit > 100:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="Limit cannot be greater than 100",
            )

        sort_direction = (
            pymongo.DESCENDING if order in ("desc", -1) else pymongo.ASCENDING
        )

        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        query: typing.Dict[typing.Text, typing.Any] = {}

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"Role with id {cursor_id} not found",
                )
            comparator = (
                "$lt"
                if (
                    (cursor_type == "after" and sort_direction == pymongo.DESCENDING)
                    or (cursor_type == "before" and sort_direction == pymongo.ASCENDING)
                )
                else "$gt"
            )
            query["_id"] = {comparator: cursor_doc["_id"]}

        # Fetch `limit + 1` docs to detect if there's a next/previous page
        logger.debug(
            f"List roles with query: {query}, "
            + f"sort: {sort_direction}, limit: {limit}"
        )
        cursor = (
            self.collection.find(query).sort([("_id", sort_direction)]).limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        # If we got an extra doc, remove it so we only return `limit` docs
        if has_more:
            docs = docs[:limit]

        # Convert raw MongoDB docs into Role models
        roles: typing.List[Role] = []
        for doc in docs:
            role = Role.model_validate(doc)
            role._id = doc["_id"]
            roles.append(role)

        first_id = roles[0].id if roles else None
        last_id = roles[-1].id if roles else None

        page = Page[Role](
            data=roles,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def update(self, id: typing.Text, role_update: RoleUpdate) -> Role:
        update_data = json.loads(role_update.model_dump_json(exclude_none=True))
        update_data["updated_at"] = int(time.time())

        try:
            updated_doc = self.collection.find_one_and_update(
                {"id": id},
                {"$set": update_data},
                return_document=pymongo.ReturnDocument.AFTER,
            )
        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="A role with this name already exists."
            ) from e

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Role with id {id} not found",
            )

        updated_role = Role.model_validate(updated_doc)
        updated_role._id = str(updated_doc["_id"])
        return updated_role

    def set_disabled(self, id: typing.Text, disabled: bool) -> Role:
        updated_doc = self.collection.find_one_and_update(
            {"id": id},
            {"$set": {"disabled": disabled, "updated_at": int(time.time())}},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Role with id {id} not found",
            )

        updated_role = Role.model_validate(updated_doc)
        updated_role._id = str(updated_doc["_id"])
        return updated_role
