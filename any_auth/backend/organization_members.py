# file: any_auth/backend/organization_members.py

import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.errors

from any_auth.types.organization_member import (
    OrganizationMember,
    OrganizationMemberCreate,
)
from any_auth.types.pagination import Page

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient, BackendIndexConfig

logger = logging.getLogger(__name__)


class OrganizationMembers:
    def __init__(self, client: "BackendClient"):
        self._client = client
        self.collection_name = "organization_members"
        self.collection: pymongo.collection.Collection = self._client.database[
            self.collection_name
        ]

    def create_indexes(
        self, index_configs: typing.Optional[typing.List["BackendIndexConfig"]] = None
    ):
        if not index_configs:
            index_configs = self._client.settings.indexes_organization_members

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

    def create(
        self,
        member_create: OrganizationMemberCreate,
        *,
        organization_id: str,
    ) -> OrganizationMember:
        doc = member_create.to_member(organization_id).to_doc()
        try:
            result = self.collection.insert_one(doc)
            _record = OrganizationMember.model_validate(doc)
            _record._id = str(result.inserted_id)
            return _record
        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="User already exists in this organization."
            ) from e

    def retrieve(self, member_id: str) -> OrganizationMember | None:
        doc = self.collection.find_one({"id": member_id})
        if not doc:
            return None
        _record = OrganizationMember.model_validate(doc)
        _record._id = str(doc["_id"])
        return _record

    def retrieve_by_organization_id(
        self, organization_id: str
    ) -> typing.List[OrganizationMember]:
        cursor = self.collection.find({"organization_id": organization_id})
        out: typing.List[OrganizationMember] = []
        for doc in cursor:
            _record = OrganizationMember.model_validate(doc)
            _record._id = str(doc["_id"])
            out.append(_record)
        return out

    def retrieve_by_user_id(self, user_id: str) -> typing.List[OrganizationMember]:
        cursor = self.collection.find({"user_id": user_id})
        out: typing.List[OrganizationMember] = []
        for doc in cursor:
            _record = OrganizationMember.model_validate(doc)
            _record._id = str(doc["_id"])
            out.append(_record)
        return out

    def list(
        self,
        *,
        organization_id: typing.Optional[str] = None,
        user_id: typing.Optional[str] = None,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[OrganizationMember]:
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
        if organization_id:
            query["organization_id"] = organization_id
        if user_id:
            query["user_id"] = user_id

        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"Organization member with id {cursor_id} not found",
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
            f"List organization members with query: {query}, "
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

        # Convert raw MongoDB docs into OrganizationMember models
        members: typing.List[OrganizationMember] = []
        for doc in docs:
            _record = OrganizationMember.model_validate(doc)
            _record._id = str(doc["_id"])
            members.append(_record)

        first_id = members[0].id if members else None
        last_id = members[-1].id if members else None

        page = Page[OrganizationMember](
            data=members,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def disable(self, member_id: str) -> OrganizationMember:
        updated_doc = self.collection.find_one_and_update(
            {"id": member_id},
            {"$set": {"disabled": True}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not updated_doc:
            raise fastapi.HTTPException(
                status_code=404, detail="Organization member not found."
            )
        _record = OrganizationMember.model_validate(updated_doc)
        _record._id = str(updated_doc["_id"])
        return _record

    def enable(self, member_id: str) -> OrganizationMember:
        updated_doc = self.collection.find_one_and_update(
            {"id": member_id},
            {"$set": {"disabled": False}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not updated_doc:
            raise fastapi.HTTPException(
                status_code=404, detail="Organization member not found."
            )
        _record = OrganizationMember.model_validate(updated_doc)
        _record._id = str(updated_doc["_id"])
        return _record

    def delete(self, member_id: str) -> None:
        self.collection.delete_one({"id": member_id})
