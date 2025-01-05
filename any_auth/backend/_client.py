import typing
from functools import cached_property

import pydantic
import pymongo
import pymongo.server_api


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
    collection_organizations: typing.Text = pydantic.Field(default="organizations")
    collection_projects: typing.Text = pydantic.Field(default="projects")  # New
    indexes_users: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_usr__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="username", direction=1)],
                name="idx_usr__username",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="email", direction=1)],
                name="idx_usr__email",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="created_at", direction=-1),
                    BackendIndexKey(field="id", direction=1),
                ],
                name="idx_usr__created_at__id",
            ),
        ]
    )
    indexes_organizations: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_org__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="name", direction=1)],
                name="idx_org__name",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="created_at", direction=-1),
                    BackendIndexKey(field="id", direction=1),
                ],
                name="idx_org__created_at__id",
            ),
        ]
    )
    indexes_projects: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_prj__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="name", direction=1)],
                name="idx_prj__name",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="created_at", direction=-1),
                    BackendIndexKey(field="organization_id", direction=1),
                    BackendIndexKey(field="id", direction=1),
                ],
                name="idx_prj__created_at__org_id__id",
            ),
        ]
    )
    indexes_resources: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_res__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="name", direction=1)],
                name="idx_res__name",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="project_id", direction=1),
                    BackendIndexKey(field="id", direction=1),
                ],
                name="idx_res__project_id__id",
                unique=False,
            ),
        ]
    )
    indexes_roles: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_rol__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="name", direction=1)],
                name="idx_rol__name",
                unique=True,
            ),
        ]
    )
    indexes_role_assignments: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_rol_ass__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="user_id", direction=1),
                    BackendIndexKey(field="project_id", direction=1),
                    BackendIndexKey(field="resource_id", direction=1),
                ],
                name="idx_rol_ass__user_id__project_id__resource_id",
                unique=False,
            ),
        ]
    )


class BackendClient:
    def __init__(
        self,
        db_client: pymongo.MongoClient | typing.Text,
        settings: typing.Optional["BackendSettings"] = None,
    ):
        self._db_client: typing.Final[pymongo.MongoClient] = (
            pymongo.MongoClient(db_client, server_api=pymongo.server_api.ServerApi("1"))
            if isinstance(db_client, typing.Text)
            else db_client
        )
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
    def organizations(self):
        from any_auth.backend.organizations import Organizations

        return Organizations(self)

    @cached_property
    def projects(self):
        from any_auth.backend.projects import Projects

        return Projects(self)

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
