import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.oauth_client import OAuthClient, OAuthClientCreate
from any_auth.types.pagination import Page

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class OAuthClients(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "oauth_clients"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_oauth_clients)

    def create(self, oauth_client_create: OAuthClientCreate) -> OAuthClient:
        oauth_client = oauth_client_create.to_oauth_client()

        try:
            result = self.collection.insert_one(oauth_client.model_dump())
            oauth_client._id = str(result.inserted_id)
            return oauth_client

        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="OAuth client already exists."
            ) from e

    def retrieve(self, oauth_client_id: str) -> OAuthClient | None:
        doc = self.collection.find_one({"id": oauth_client_id})
        if not doc:
            return None
        return OAuthClient.model_validate(doc)

    def retrieve_by_client_id(self, client_id: str) -> OAuthClient | None:
        doc = self.collection.find_one({"client_id": client_id})
        if not doc:
            return None
        return OAuthClient.model_validate(doc)

    def list(
        self,
        *,
        project_id: typing.Optional[str] = None,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[OAuthClient]:
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
        if project_id is not None:
            query["project_id"] = project_id

        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"OAuth client with id {cursor_id} not found",
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
            f"List OAuth clients with query: {query}, "
            + f"sort: {sort_direction}, limit: {limit}"
        )
        cursor = (
            self.collection.find(query).sort("_id", sort_direction).limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        if has_more:
            docs = docs[:limit]

        # Convert raw MongoDB docs into OAuthClient models
        oauth_clients: typing.List[OAuthClient] = []
        for doc in docs:
            oauth_client = OAuthClient.model_validate(doc)
            oauth_client._id = str(doc["_id"])
            oauth_clients.append(oauth_client)

        first_id = oauth_clients[0].id if oauth_clients else None
        last_id = oauth_clients[-1].id if oauth_clients else None

        page = Page[OAuthClient](
            data=oauth_clients,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def set_disabled(self, id: str, disabled: bool) -> OAuthClient:
        updated_doc = self.collection.find_one_and_update(
            {"id": id},
            {"$set": {"disabled": disabled}},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"OAuth client with id {id} not found",
            )

        return OAuthClient.model_validate(updated_doc)

    def set_disabled_by_client_id(self, client_id: str, disabled: bool) -> OAuthClient:
        updated_doc = self.collection.find_one_and_update(
            {"client_id": client_id},
            {"$set": {"disabled": disabled}},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"OAuth client with client_id {client_id} not found",
            )

        return OAuthClient.model_validate(updated_doc)
