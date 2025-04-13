import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.invite import InviteCreate, InviteInDB
from any_auth.types.pagination import Page

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Invites(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "invites"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_invites)

    def create(
        self,
        invite_create: InviteCreate,
        *,
        resource_id: typing.Text,
        invited_by: typing.Text,
        expires_in: int = 15 * 60,  # 15 minutes in seconds
    ) -> InviteInDB:
        # Create new invite
        invite_in_db = invite_create.to_invite(
            resource_id=resource_id, invited_by=invited_by, expires_in=expires_in
        )
        doc = invite_in_db.to_doc()

        try:
            result = self.collection.insert_one(doc)
            invite_in_db._id = str(result.inserted_id)

            return invite_in_db

        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409,
                detail="Invite for this email already exists in this project.",
            ) from e

    def retrieve(self, invite_id: typing.Text) -> InviteInDB | None:
        """Retrieve a project invite by ID."""

        # Get from database
        doc = self.collection.find_one({"id": invite_id})
        if not doc:
            return None

        # Create record and update cache
        invite_in_db = InviteInDB.model_validate(doc)
        invite_in_db._id = str(doc["_id"])

        return invite_in_db

    def retrieve_by_email_and_resource_id(
        self,
        email: typing.Text,
        resource_id: typing.Text,
    ) -> InviteInDB | None:
        """Retrieve a project invite by email and project ID."""

        # Get from database
        doc = self.collection.find_one({"email": email, "resource_id": resource_id})
        if not doc:
            return None

        # Create record and update cache
        invite_in_db = InviteInDB.model_validate(doc)
        invite_in_db._id = str(doc["_id"])

        return invite_in_db

    def retrieve_by_temporary_token(
        self,
        temporary_token: typing.Text,
        *,
        email: typing.Text | None = None,
        resource_id: typing.Text | None = None,
    ) -> InviteInDB | None:
        """Retrieve a project invite by email and project ID."""

        # Get from database
        query = {"temporary_token": temporary_token}
        if email:
            query["email"] = email
        if resource_id:
            query["resource_id"] = resource_id

        doc = self.collection.find_one(query)
        if not doc:
            return None

        # Create record and update cache
        invite_in_db = InviteInDB.model_validate(doc)
        invite_in_db._id = str(doc["_id"])

        return invite_in_db

    def list(
        self,
        *,
        resource_id: typing.Text | None = None,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[InviteInDB]:
        limit = limit or 20
        if limit > 100:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="Limit cannot be greater than 100",
            )

        sort_direction = (
            pymongo.DESCENDING if order in ("desc", -1) else pymongo.ASCENDING
        )

        query = {}
        if resource_id:
            query["resource_id"] = resource_id

        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"Invite with id {cursor_id} not found",
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
            f"List invites with query: {query}, "
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

        # Convert raw MongoDB docs into Invite models
        invites: typing.List[InviteInDB] = []
        for doc in docs:
            invite = InviteInDB.model_validate(doc)
            invite._id = doc["_id"]
            invites.append(invite)

        first_id = invites[0].id if invites else None
        last_id = invites[-1].id if invites else None

        page = Page[InviteInDB](
            data=invites,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def delete(self, invite_id: typing.Text) -> None:
        """Delete a project invite by ID."""
        # Get the invite first to clear cache properly
        invite = self.retrieve(invite_id)
        if not invite:
            return

        # Delete from database
        self.collection.delete_one({"id": invite_id})
