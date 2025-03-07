import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.pagination import Page
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class ProjectMembers(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "project_members"

    @typing.override
    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_project_members)

    def create(
        self,
        member_create: ProjectMemberCreate,
        *,
        project_id: str,
        exists_ok: bool = True,
    ) -> ProjectMember:
        doc = self.collection.find_one(
            {"user_id": member_create.user_id, "project_id": project_id}
        )
        if doc:
            if exists_ok:
                _record = ProjectMember.model_validate(doc)
                _record._id = str(doc["_id"])
                return _record
            else:
                raise fastapi.HTTPException(
                    status_code=409, detail="User already exists in this project."
                )

        doc = member_create.to_member(project_id).to_doc()
        try:
            result = self.collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            _record = ProjectMember.model_validate(doc)
            _record._id = str(doc["_id"])

            # Delete cache
            self._client.cache.delete(f"project_member:{_record.id}")
            self._client.cache.delete(
                f"project_member_by_project_user_id:{_record.project_id}:{_record.user_id}"  # noqa: E501
            )

            return _record
        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="User already exists in this project."
            ) from e

    def retrieve(self, member_id: str) -> ProjectMember | None:
        # Get from cache
        cached_member = self._client.cache.get(f"project_member:{member_id}")
        if cached_member:
            return ProjectMember.model_validate_json(cached_member)  # type: ignore

        doc = self.collection.find_one({"id": member_id})
        if not doc:
            return None
        _record = ProjectMember.model_validate(doc)
        _record._id = str(doc["_id"])

        # Cache
        self._client.cache.set(
            f"project_member:{_record.id}",
            _record.model_dump_json(),
            self._client.cache_ttl,
        )

        return _record

    def retrieve_by_project_user_id(
        self, project_id: str, user_id: str
    ) -> typing.Optional[ProjectMember]:
        # Get from cache
        cached_member = self._client.cache.get(
            f"project_member_by_project_user_id:{project_id}:{user_id}"
        )
        if cached_member:
            return ProjectMember.model_validate_json(cached_member)  # type: ignore

        doc = self.collection.find_one({"project_id": project_id, "user_id": user_id})
        if not doc:
            return None
        _record = ProjectMember.model_validate(doc)
        _record._id = str(doc["_id"])

        # Cache
        self._client.cache.set(
            f"project_member_by_project_user_id:{project_id}:{user_id}",
            _record.model_dump_json(),
            self._client.cache_ttl,
        )

        return _record

    def retrieve_by_project_id(self, project_id: str) -> typing.List[ProjectMember]:
        cursor = self.collection.find({"project_id": project_id})
        out: typing.List[ProjectMember] = []
        for doc in cursor:
            _record = ProjectMember.model_validate(doc)
            _record._id = str(doc["_id"])
            out.append(_record)
        return out

    def retrieve_by_user_id(self, user_id: str) -> typing.List[ProjectMember]:
        cursor = self.collection.find({"user_id": user_id})
        out: typing.List[ProjectMember] = []
        for doc in cursor:
            _record = ProjectMember.model_validate(doc)
            _record._id = str(doc["_id"])
            out.append(_record)
        return out

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
            _record = ProjectMember.model_validate(doc)
            _record._id = str(doc["_id"])
            members.append(_record)

        first_id = members[0].id if members else None
        last_id = members[-1].id if members else None

        page = Page[ProjectMember](
            data=members,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def delete(self, member_id: str) -> None:
        self.collection.delete_one({"id": member_id})

        # Delete cache
        self._client.cache.delete(f"project_member:{member_id}")
