import logging
import typing

import diskcache
import pydantic
import redis

from any_auth.utils.dummy_cache import DummyCache

if typing.TYPE_CHECKING:
    from any_auth.config import Settings

logger = logging.getLogger(__name__)


DATABASE_NAME_DEFAULT = "auth"
TABLE_USERS_DEFAULT = "users"
TABLE_ROLES_DEFAULT = "roles"
TABLE_ROLE_ASSIGNMENTS_DEFAULT = "role_assignments"
TABLE_ORGANIZATIONS_DEFAULT = "organizations"
TABLE_PROJECTS_DEFAULT = "projects"
TABLE_ORGANIZATION_MEMBERS_DEFAULT = "organization_members"
TABLE_PROJECT_MEMBERS_DEFAULT = "project_members"
TABLE_API_KEYS_DEFAULT = "api_keys"


class BackendIndexKey(pydantic.BaseModel):
    field: typing.Text
    direction: typing.Literal[1, -1]


class BackendIndexConfig(pydantic.BaseModel):
    keys: typing.List[BackendIndexKey]
    name: typing.Text
    unique: bool = False


class DatabaseNameSettings(pydantic.BaseModel):
    database: typing.Text = pydantic.Field(default=DATABASE_NAME_DEFAULT)


class CollectionUsersSettings(pydantic.BaseModel):
    collection_users: typing.Text = pydantic.Field(default=TABLE_USERS_DEFAULT)

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
        ]
    )


class CollectionOrganizationsSettings(pydantic.BaseModel):
    collection_organizations: typing.Text = pydantic.Field(
        default=TABLE_ORGANIZATIONS_DEFAULT
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
        ]
    )


class CollectionProjectsSettings(pydantic.BaseModel):
    collection_projects: typing.Text = pydantic.Field(default=TABLE_PROJECTS_DEFAULT)

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
                keys=[BackendIndexKey(field="organization_id", direction=1)],
                name="idx_prj__org_id",
            ),
        ]
    )


class CollectionRolesSettings(pydantic.BaseModel):
    collection_roles: typing.Text = pydantic.Field(default=TABLE_ROLES_DEFAULT)

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


class CollectionRoleAssignmentsSettings(pydantic.BaseModel):
    collection_role_assignments: typing.Text = pydantic.Field(
        default=TABLE_ROLE_ASSIGNMENTS_DEFAULT
    )
    indexes_role_assignments: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_rol_ass__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="user_id", direction=1)],
                name="idx_rol_ass__user_id",
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="resource_id", direction=1)],
                name="idx_rol_ass__resource_id",
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="role_id", direction=1)],
                name="idx_rol_ass__role_id",
            ),
        ]
    )


class CollectionOrganizationMembersSettings(pydantic.BaseModel):
    collection_organization_members: typing.Text = pydantic.Field(
        default=TABLE_ORGANIZATION_MEMBERS_DEFAULT
    )

    indexes_organization_members: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_org_members__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="organization_id", direction=1)],
                name="idx_org_members__org_id",
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="user_id", direction=1)],
                name="idx_org_members__user_id",
            ),
        ]
    )


class CollectionProjectMembersSettings(pydantic.BaseModel):
    collection_project_members: typing.Text = pydantic.Field(
        default=TABLE_PROJECT_MEMBERS_DEFAULT
    )

    indexes_project_members: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_proj_members__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="project_id", direction=1)],
                name="idx_proj_members__proj_id",
            ),
            BackendIndexConfig(
                keys=[BackendIndexKey(field="user_id", direction=1)],
                name="idx_proj_members__user_id",
            ),
        ]
    )


class CollectionAPIKeysSettings(pydantic.BaseModel):
    collection_api_keys: typing.Text = pydantic.Field(default=TABLE_API_KEYS_DEFAULT)

    indexes_api_keys: typing.List[BackendIndexConfig] = pydantic.Field(
        default_factory=lambda: [
            BackendIndexConfig(
                keys=[BackendIndexKey(field="id", direction=1)],
                name="idx_api_keys__id",
                unique=True,
            ),
            BackendIndexConfig(
                keys=[
                    BackendIndexKey(field="decorator", direction=1),
                    BackendIndexKey(field="prefix", direction=1),
                ],
                name="idx_api_keys__decorator_prefix",
            ),
        ]
    )


class BackendSettings(
    DatabaseNameSettings,
    CollectionUsersSettings,
    CollectionOrganizationsSettings,
    CollectionProjectsSettings,
    CollectionRolesSettings,
    CollectionRoleAssignmentsSettings,
    CollectionOrganizationMembersSettings,
    CollectionProjectMembersSettings,
    CollectionAPIKeysSettings,
):
    # Fields definitions

    # Private attributes
    _cache: typing.Optional[diskcache.Cache | redis.Redis | DummyCache] = (
        pydantic.PrivateAttr(default=None)
    )
    _cache_ttl: int = pydantic.PrivateAttr(default=15 * 60)  # 15 minutes

    @classmethod
    def from_any_auth_settings(
        cls,
        settings: "Settings",
        *,
        database_name: typing.Optional[typing.Text] = None,
        cache_ttl: int = 15 * 60,  # 15 minutes
        cache: typing.Optional[diskcache.Cache | redis.Redis | DummyCache] = None,
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

        if not cache_ttl or cache_ttl <= 0 or cache_ttl > 60 * 60 * 24 * 30:
            raise ValueError("Invalid cache TTL, must be between 1 second and 30 days")

        _backend_settings._cache_ttl = cache_ttl
        _backend_settings._cache = (
            cache if cache is not None else settings.cache or DummyCache()
        )

        return _backend_settings
