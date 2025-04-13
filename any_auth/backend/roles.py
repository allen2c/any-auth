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
from any_auth.types.pagination import Page
from any_auth.types.role import Role, RoleCreate, RoleListAdapter, RoleUpdate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Roles(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "roles"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_roles)

    def create(self, role_create: RoleCreate) -> Role:
        if role_create.parent_id is not None:
            parent_role = self.retrieve_by_id_or_name(role_create.parent_id)
            if parent_role is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"Parent role with id {role_create.parent_id} not found",
                )
            role_create = role_create.model_copy(update={"parent_id": parent_role.id})

        role = role_create.to_role()
        result = self.collection.insert_one(role.to_doc())
        role._id = str(result.inserted_id)

        logger.info(f"Role created: {role.model_dump_json()}")

        # Delete cache
        self._client.cache.delete(f"role:{role.id}")
        self._client.cache.delete(f"retrieve_all_child_roles:{role.id}")
        self._client.cache.delete(f"retrieve_all_child_roles:{role.parent_id}")
        return role

    def retrieve(self, id: typing.Text) -> typing.Optional[Role]:
        # Get from cache
        cached_role = self._client.cache.get(f"role:{id}")
        if cached_role:
            return Role.model_validate_json(cached_role)  # type: ignore

        role_data = self.collection.find_one({"id": id})
        if role_data:
            role = Role.model_validate(role_data)
            role._id = str(role_data["_id"])

            # Cache
            self._client.cache.set(
                f"role:{id}",
                role.model_dump_json(),
                self._client.cache_ttl,
            )

            return role

        return None

    def retrieve_by_name(self, name: typing.Text) -> typing.Optional[Role]:
        # Get from cache
        cached_role = self._client.cache.get(f"role_by_name:{name}")
        if cached_role:
            return Role.model_validate_json(cached_role)  # type: ignore

        role_data = self.collection.find_one({"name": name})
        if role_data:
            role = Role.model_validate(role_data)
            role._id = str(role_data["_id"])

            # Cache
            self._client.cache.set(
                f"role_by_name:{name}",
                role.model_dump_json(),
                self._client.cache_ttl,
            )

            return role

        return None

    def retrieve_by_id_or_name(self, name_or_id: typing.Text) -> typing.Optional[Role]:
        role_data = self.retrieve(name_or_id) or self.retrieve_by_name(name_or_id)
        return role_data

    def retrieve_by_ids(self, ids: typing.List[typing.Text]) -> typing.List[Role]:
        if not ids:
            logger.warning("No role IDs provided")
            return []
        docs = list(self.collection.find({"id": {"$in": ids}}))
        roles: typing.List[Role] = []
        for doc in docs:
            role = Role.model_validate(doc)
            role._id = doc["_id"]
            roles.append(role)
        return roles

    def retrieve_by_target_id(
        self,
        target_id: typing.Text,
        resource_id: typing.Text,
    ) -> typing.List[Role]:
        assignments = self._client.role_assignments.retrieve_by_target_id(
            target_id=target_id, resource_id=resource_id
        )

        if not assignments:
            return []

        roles = self.retrieve_by_ids([assignment.role_id for assignment in assignments])
        return roles

    def retrieve_by_parent_id(self, parent_id: typing.Text) -> typing.List[Role]:
        if not parent_id:
            logger.warning(
                "No parent ID provided. Use `retrieve_top_level_roles` instead if "
                "you want to retrieve all top level roles."
            )
            return []

        docs = list(self.collection.find({"parent_id": parent_id}))
        roles: typing.List[Role] = []
        for doc in docs:
            role = Role.model_validate(doc)
            role._id = doc["_id"]
            roles.append(role)

        return roles

    def retrieve_all_child_roles(
        self,
        id: typing.Text,
        roles_map: typing.Optional[typing.Dict[typing.Text, Role]] = None,
    ) -> typing.List[Role]:
        roles_map = roles_map or {}

        # Get from cache
        cached_roles = self._client.cache.get(f"retrieve_all_child_roles:{id}")
        if cached_roles:
            roles = RoleListAdapter.validate_json(cached_roles)  # type: ignore

        else:
            roles = self.retrieve_by_parent_id(id)

            # Cache
            self._client.cache.set(
                f"retrieve_all_child_roles:{id}",
                RoleListAdapter.dump_json(roles),
                self._client.cache_ttl,
            )

        for role in roles:
            if role.id in roles_map:
                logger.error(f"Cycle detected in role hierarchy: {role.id} -> {id}")
                break
            roles_map[role.id] = role
            roles_map.update(
                {
                    role.id: role
                    for role in self.retrieve_all_child_roles(role.id, roles_map)
                }
            )

        return list(roles_map.values())

    def retrieve_top_level_roles(self) -> typing.List[Role]:
        docs = list(
            self.collection.find(
                {"$or": [{"parent_id": None}, {"parent_id": {"$exists": False}}]}
            )
        )
        roles: typing.List[Role] = []
        for doc in docs:
            role = Role.model_validate(doc)
            role._id = doc["_id"]
            roles.append(role)
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

        logger.info(f"Role updated: {updated_role.model_dump_json()}")

        # Delete cache
        self._client.cache.delete(f"role:{updated_role.id}")
        self._client.cache.delete(f"retrieve_all_child_roles:{updated_role.id}")
        self._client.cache.delete(f"retrieve_all_child_roles:{updated_role.parent_id}")

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

        logger.info(f"Role disabled: {updated_role.model_dump_json()}")

        # Delete cache
        self._client.cache.delete(f"role:{updated_role.id}")
        self._client.cache.delete(f"retrieve_all_child_roles:{updated_role.id}")
        self._client.cache.delete(f"retrieve_all_child_roles:{updated_role.parent_id}")

        return updated_role
