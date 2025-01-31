import logging
import typing
from functools import cached_property

import httpx
import pydantic
import pymongo
import pymongo.server_api

if typing.TYPE_CHECKING:
    from any_auth.config import Settings

logger = logging.getLogger(__name__)


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
    collection_organizations: typing.Text = pydantic.Field(default="organizations")
    collection_projects: typing.Text = pydantic.Field(default="projects")
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
            BackendIndexConfig(
                keys=[BackendIndexKey(field="parent_id", direction=1)],
                name="idx_rol__parent_id",
                unique=False,
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
                    BackendIndexKey(field="resource_id", direction=1),
                ],
                name="idx_rol_ass__user_id__resource_id",
                unique=False,
            ),
        ]
    )
    indexes_organization_members: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_org_members__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="organization_id", direction=1),
                    BackendIndexKey(field="user_id", direction=1),
                ],
                name="idx_org_members__org_id__user_id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="organization_id", direction=1)],
                name="idx_org_members__org_id",
                unique=False,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="user_id", direction=1)],
                name="idx_org_members__user_id",
                unique=False,
            ),
        ]
    )
    indexes_project_members: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_proj_members__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="project_id", direction=1),
                    BackendIndexKey(field="user_id", direction=1),
                ],
                name="idx_proj_members__proj_id__user_id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="project_id", direction=1)],
                name="idx_proj_members__proj_id",
                unique=False,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="user_id", direction=1)],
                name="idx_proj_members__user_id",
                unique=False,
            ),
        ]
    )

    @classmethod
    def from_settings(
        cls, settings: "Settings", *, database_name: typing.Optional[typing.Text] = None
    ):
        _backend_settings = (
            BackendSettings()
            if database_name is None
            else BackendSettings(database=database_name)
        )

        # Force post-fixing database name if not provided by env
        if database_name is None:
            # Set database name based on environment
            if settings.ENVIRONMENT != "production":
                logger.info(
                    "Application environment is not 'production', adding "
                    + f"environment '{settings.ENVIRONMENT}' to database name"
                )
                _backend_settings.database += f"_{settings.ENVIRONMENT}"
                logger.info(
                    f"Database name from environment '{settings.ENVIRONMENT}': "
                    + f"'{_backend_settings.database}'"
                )

        return _backend_settings


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

    @classmethod
    def from_settings(
        cls,
        settings: "Settings",
        *,
        backend_settings: "BackendSettings",
    ):
        _backend_client = BackendClient(
            pymongo.MongoClient(
                str(httpx.URL(settings.DATABASE_URL.get_secret_value()))
            ),
            backend_settings,
        )

        return _backend_client

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
    def role_assignments(self):
        from any_auth.backend.role_assignments import RoleAssignments

        return RoleAssignments(self)

    @cached_property
    def organization_members(self):
        from any_auth.backend.organization_members import OrganizationMembers

        return OrganizationMembers(self)

    @cached_property
    def project_members(self):
        from any_auth.backend.project_members import ProjectMembers

        return ProjectMembers(self)

    def touch(self, with_indexes: bool = True):
        logger.debug("Touching backend")

        if with_indexes:
            self.users.create_indexes()
            self.organizations.create_indexes()
            self.projects.create_indexes()
            self.roles.create_indexes()
            self.role_assignments.create_indexes()
            self.organization_members.create_indexes()
            self.project_members.create_indexes()

    def close(self):
        logger.debug("Closing backend")
        self._db_client.close()
