import json
import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.database
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
)
from any_auth.types.pagination import Page

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class APIKeys(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "api_keys"

    def create_indexes(
        self,
        *args,
        **kwargs,
    ):
        super().create_indexes(self.settings.indexes_api_keys)

    def create(
        self,
        api_key_create: APIKeyCreate | None = None,
        *,
        resource_id: typing.Text,
        user_id: typing.Text,
    ) -> APIKey:
        if api_key_create is None:
            api_key_create = APIKeyCreate()
        api_key = api_key_create.to_api_key(
            resource_id=resource_id,
            user_id=user_id,
        )

        doc = api_key.model_dump()

        try:
            result = self.collection.insert_one(doc)
            api_key._id = str(result.inserted_id)

        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="API Key already exists"
            ) from e

        return api_key

    def retrieve(self, api_key_id: typing.Text) -> APIKey | None:
        doc = self.collection.find_one({"_id": api_key_id})
        if doc:
            api_key = APIKey.model_validate(doc)
            api_key._id = str(doc["_id"])
            return api_key
        return None

    def list(
        self,
        *,
        resource_id: typing.Text | None = None,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[APIKey]:
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
        if resource_id:
            query["resource_id"] = resource_id

        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"API Key with id {cursor_id} not found",
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
            f"List API keys with query: {query}, "
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

        # Convert raw MongoDB docs into APIKey models
        api_keys: typing.List[APIKey] = []
        for doc in docs:
            _record = APIKey.model_validate(doc)
            _record._id = str(doc["_id"])
            api_keys.append(_record)

        first_id = api_keys[0].id if api_keys else None
        last_id = api_keys[-1].id if api_keys else None

        page = Page[APIKey](
            data=api_keys,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def update(self, api_key_id: typing.Text, api_key_update: APIKeyUpdate) -> APIKey:
        update_data = json.loads(api_key_update.model_dump_json(exclude_none=True))

        try:
            updated_doc = self.collection.find_one_and_update(
                {"id": api_key_id},
                {"$set": update_data},
                return_document=pymongo.ReturnDocument.AFTER,
            )
        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="An API Key with this name already exists."
            ) from e

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"API Key with id {api_key_id} not found",
            )

        updated_api_key = APIKey.model_validate(updated_doc)
        updated_api_key._id = str(updated_doc["_id"])

        return updated_api_key

    def delete(self, api_key_id: typing.Text) -> None:
        self.collection.delete_one({"id": api_key_id})
