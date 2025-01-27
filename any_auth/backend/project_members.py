import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.errors

from any_auth.types.pagination import Page
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient, BackendIndexConfig

logger = logging.getLogger(__name__)


class ProjectMembers:
    def __init__(self, client: "BackendClient"):
        self._client = client
        self.collection_name = "project_members"
        self.collection: pymongo.collection.Collection = self._client.database[
            self.collection_name
        ]

    def create_indexes(
        self, index_configs: typing.Optional[typing.List["BackendIndexConfig"]] = None
    ):
        if not index_configs:
            index_configs = self._client.settings.indexes_project_members

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
        logger.info(f"Created indexes for {self.collection_name}: {created_indexes}")

    def create(self, member_create: ProjectMemberCreate) -> ProjectMember:
        doc = member_create.to_member().to_doc()
        try:
            result = self.collection.insert_one(doc)
            doc["id"] = str(result.inserted_id)
            return ProjectMember.model_validate(doc)
        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="User already exists in this project."
            ) from e

    def retrieve(self, member_id: str) -> ProjectMember | None:
        doc = self.collection.find_one({"id": member_id})
        if not doc:
            return None
        return ProjectMember.model_validate(doc)

    def list(
        self,
        *,
        project_id: typing.Optional[str] = None,
        user_id: typing.Optional[str] = None,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[ProjectMember]:
        limit = limit or 20
        if limit > 100:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="Limit cannot be greater than 100",
            )

        sort_direction = (
            pymongo.DESCENDING if order in ("desc", -1) else pymongo.ASCENDING
        )

        query: typing.Dict[typing.Text, typing.Any] = {}
        if project_id:
            query["project_id"] = project_id
        if user_id:
            query["user_id"] = user_id

        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"Project member with id {cursor_id} not found",
                )
            comparator = (
                "$lt"
                if (
                    (cursor_type == "after" and sort_direction == pymongo.DESCENDING)
                    or (cursor_type == "before" and sort_direction == pymongo.ASCENDING)
                )
                else "$gt"
            )
            query["$or"] = [
                {"joined_at": {comparator: cursor_doc["joined_at"]}},
                {
                    "joined_at": cursor_doc["joined_at"],
                    "id": {comparator: cursor_doc["id"]},
                },
            ]

        # Fetch `limit + 1` docs to detect if there's a next/previous page
        logger.debug(
            f"List project members with query: {query}, "
            + f"sort: {sort_direction}, limit: {limit}"
        )
        cursor = (
            self.collection.find(query)
            .sort([("joined_at", sort_direction), ("id", sort_direction)])
            .limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        # If we got an extra doc, remove it so we only return `limit` docs
        if has_more:
            docs = docs[:limit]

        # Convert raw MongoDB docs into ProjectMember models
        members: typing.List[ProjectMember] = []
        for doc in docs:
            member = ProjectMember.model_validate(doc)
            members.append(member)

        first_id = members[0].id if members else None
        last_id = members[-1].id if members else None

        page = Page[ProjectMember](
            data=members,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def disable(self, member_id: str) -> ProjectMember:
        updated_doc = self.collection.find_one_and_update(
            {"id": member_id},
            {"$set": {"disabled": True}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not updated_doc:
            raise fastapi.HTTPException(
                status_code=404, detail="Project member not found."
            )
        return ProjectMember.model_validate(updated_doc)

    def enable(self, member_id: str) -> ProjectMember:
        updated_doc = self.collection.find_one_and_update(
            {"id": member_id},
            {"$set": {"disabled": False}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not updated_doc:
            raise fastapi.HTTPException(
                status_code=404, detail="Project member not found."
            )
        return ProjectMember.model_validate(updated_doc)

    def delete(self, member_id: str) -> None:
        self.collection.delete_one({"id": member_id})
