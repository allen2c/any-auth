import logging
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.pagination import Page
from any_auth.types.user import UserInDB

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient, BackendIndexConfig


logger = logging.getLogger(__name__)


class Users:
    def __init__(self, client: "BackendClient"):
        self._client: typing.Final["BackendClient"] = client
        self.collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_users
        )
        self.collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.collection_name]
        )

    def create_indexes(
        self, index_configs: typing.Optional[typing.List["BackendIndexConfig"]] = None
    ):
        if index_configs is None:
            index_configs = self._client.settings.indexes_users

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

    def retrieve(self, id: typing.Text) -> typing.Optional[UserInDB]:
        doc = self.collection.find_one({"id": id})
        if doc is None:
            return None
        user = UserInDB.model_validate(doc)
        user._id = str(doc["_id"])
        return user

    def list(
        self,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[UserInDB]:
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
        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {cursor_id} not found",
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
                {"created_at": {comparator: cursor_doc["created_at"]}},
                {
                    "created_at": cursor_doc["created_at"],
                    "id": {comparator: cursor_doc["id"]},
                },
            ]

        # Fetch `limit + 1` docs to detect if there's a next/previous page
        logger.debug(
            f"List users with query: {query}, "
            + f"sort: {sort_direction}, limit: {limit}"
        )
        cursor = (
            self.collection.find(query)
            .sort([("created_at", sort_direction), ("id", sort_direction)])
            .limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        # If we got an extra doc, remove it so we only return `limit` docs
        if has_more:
            docs = docs[:limit]

        # Convert raw MongoDB docs into User models
        users: typing.List[UserInDB] = []
        for doc in docs:
            user = UserInDB.model_validate(doc)
            user._id = doc["_id"]
            users.append(user)

        first_id = users[0].id if users else None
        last_id = users[-1].id if users else None

        page = Page[UserInDB](
            data=users,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page
