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
    collection_roles: typing.Text = pydantic.Field(default="roles")
    collection_role_assignments: typing.Text = pydantic.Field(
        default="role_assignments"
    )
    collection_resources: typing.Text = pydantic.Field(default="resources")
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
        self._db_client: typing.Final[pymongo.MongoClient] = db_client
        self._settings: typing.Final[BackendSettings] = (
            BackendSettings.model_validate_json(settings.model_dump_json())
            if settings is not None
            else BackendSettings()
        )

    @property
    def settings(self):
        return self._settings

    @property
    def database_client(self):
        return self._db_client

    @property
    def database(self):
        return self._db_client[self._settings.database]

    @cached_property
    def users(self):
        from any_auth.backend.users import Users

        return Users(self)

    @cached_property
    def roles(self):
        from any_auth.backend.roles import Roles

        return Roles(self)

    @cached_property
    def resources(self):
        from any_auth.backend.resources import Resources

        return Resources(self)
