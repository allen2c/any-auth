import typing
from functools import cached_property

import pydantic
import pymongo


class BackendIndexKey(pydantic.BaseModel):
    field: typing.Text
    direction: typing.Literal[1, -1]


class BackendIndexConfig(pydantic.BaseModel):
    keys: typing.List[BackendIndexKey]
    name: typing.Text
    unique: bool = False


class BackendSettings(pydantic.BaseModel):
    database: typing.Text = pydantic.Field(default="auth")
    collection_users: typing.Text = pydantic.Field(default="users")
    indexes_users: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_users_id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="username", direction=1)],
                name="idx_users_username",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="email", direction=1)],
                name="idx_users_email",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="created_at", direction=-1),
                    BackendIndexKey(field="id", direction=1),
                ],
                name="idx_users_created_at_id",
            ),
        ]
    )


class BackendClient:
    def __init__(
        self,
        db_client: pymongo.MongoClient,
        settings: typing.Optional[BackendSettings] = None,
    ):
        self.db_client = db_client
        self.settings = (
            BackendSettings.model_validate_json(settings.model_dump_json())
            if settings is not None
            else BackendSettings()
        )

    @cached_property
    def users(self):
        from any_auth.backend.users import Users

        return Users(self)
