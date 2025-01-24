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
from any_auth.types.user import UserCreate, UserInDB, UserUpdate

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
        logger.info(
            f"Created collection '{self.collection_name}' indexes: {created_indexes}"
        )

    def create(self, user_create: UserCreate) -> UserInDB:
        user_in_db = user_create.to_user_in_db()
        doc = user_in_db.to_doc()
        try:
            result = self.collection.insert_one(doc)
            user_in_db._id = str(result.inserted_id)
            return user_in_db
        except pymongo.errors.DuplicateKeyError as e:
            # Extract the field that caused the duplication from the error details
            if e.details is not None:
                duplicated_fields_expr = ", ".join(
                    list(e.details.get("keyPattern", {}).keys())
                )
                error_message = (
                    f"A user with this {duplicated_fields_expr} already exists."
                )
            else:
                error_message = "A user with this username or email already exists."
            raise fastapi.HTTPException(
                status_code=409, detail=error_message  # 409 Conflict
            )

    def retrieve(self, id: typing.Text) -> typing.Optional[UserInDB]:
        doc = self.collection.find_one({"id": id})
        if doc is None:
            return None
        user = UserInDB.model_validate(doc)
        user._id = str(doc["_id"])
        return user

    def retrieve_by_username(self, username: typing.Text) -> typing.Optional[UserInDB]:
        doc = self.collection.find_one({"username": username})
        if doc is None:
            return None
        user = UserInDB.model_validate(doc)
        user._id = str(doc["_id"])
        return user

    def retrieve_by_email(self, email: typing.Text) -> typing.Optional[UserInDB]:
        doc = self.collection.find_one({"email": email})
        if doc is None:
            return None
        user = UserInDB.model_validate(doc)
        user._id = str(doc["_id"])
        return user

    def list(
        self,
        *,
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

    def update(self, id: typing.Text, user_update: UserUpdate) -> UserInDB:
        update_data = json.loads(user_update.model_dump_json(exclude_none=True))
        update_data["updated_at"] = int(time.time())

        try:
            updated_doc = self.collection.find_one_and_update(
                {"id": id},
                {"$set": update_data},
                return_document=pymongo.ReturnDocument.AFTER,
            )
        except pymongo.errors.DuplicateKeyError as e:
            # Extract the field that caused the duplication from the error details
            if e.details is not None:
                duplicated_fields_expr = ", ".join(
                    list(e.details.get("keyPattern", {}).keys())
                )
                error_message = (
                    f"A user with this {duplicated_fields_expr} already exists."
                )
                raise fastapi.HTTPException(
                    status_code=409, detail=error_message  # 409 Conflict
                )

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"User with id {id} not found",
            )

        updated_user = UserInDB.model_validate(updated_doc)
        updated_user._id = str(updated_doc["_id"])
        return updated_user

    def set_disabled(self, id: typing.Text, disabled: bool) -> UserInDB:
        updated_doc = self.collection.find_one_and_update(
            {"id": id},
            {"$set": {"disabled": disabled}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"User with id {id} not found",
            )
        updated_user = UserInDB.model_validate(updated_doc)
        updated_user._id = str(updated_doc["_id"])
        return updated_user

    def reset_password(self, id: typing.Text, new_password: typing.Text) -> UserInDB:
        _hashed_password = UserInDB.hash_password(new_password)
        updated_doc = self.collection.find_one_and_update(
            {"id": id},
            {"$set": {"hashed_password": _hashed_password}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"User with id {id} not found",
            )
        return UserInDB.model_validate(updated_doc)
