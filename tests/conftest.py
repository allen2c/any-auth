import logging
import os
import time
import typing
import uuid

import httpx
import pymongo
import pymongo.errors
import pytest
from faker import Faker
from logging_bullet_train import set_logger

if typing.TYPE_CHECKING:
    from any_auth.backend import BackendClient
    from any_auth.config import Settings
    from any_auth.types.oauth_client import OAuthClient
    from any_auth.types.organization import Organization
    from any_auth.types.organization_member import OrganizationMember
    from any_auth.types.project import Project
    from any_auth.types.project_member import ProjectMember
    from any_auth.types.role import Role
    from any_auth.types.role_assignment import RoleAssignment
    from any_auth.types.user import UserInDB

set_logger("any_auth")
set_logger("tests")

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PYTEST_CURRENT_TEST"] = "true"
    os.environ["IS_TEST"] = "true"
    os.environ["IS_TESTING"] = "true"
    os.environ["PYTEST_RUNNING"] = "true"


@pytest.fixture(scope="module")
def deps_fake():
    from faker import Faker

    return Faker()


@pytest.fixture(scope="module")
def deps_backend_database_name():
    return f"auth_test_{int(time.time())}_{str(uuid.uuid4())[:8]}"


@pytest.fixture(scope="module")
def deps_org_name(deps_fake: Faker):
    return f"org_{deps_fake.user_name()}"


@pytest.fixture(scope="module")
def deps_proj_name(deps_fake: Faker):
    return f"project_{deps_fake.user_name()}"


@pytest.fixture(scope="module")
def deps_settings():
    from any_auth.config import Settings

    settings = Settings()  # type: ignore
    assert settings.ENVIRONMENT == "test", "Settings must be in test environment"

    return settings


@pytest.fixture(scope="module")
def deps_backend_client_session(
    deps_settings: "Settings", deps_backend_database_name: typing.Text
):
    assert (
        "test" in deps_backend_database_name.lower()
    ), "Backend database name must contain 'test'"

    def ensure_client(url: httpx.URL, *, with_indexes: bool = True):
        return _init_backend_client(
            _validate_db_client(_new_db_client(url)),
            settings=deps_settings,
            backend_database_name=deps_backend_database_name,
            with_indexes=with_indexes,
        )

    db_url = httpx.URL(deps_settings.DATABASE_URL.get_secret_value())

    client = ensure_client(url=db_url, with_indexes=True)

    yield client

    # Teardown: Drop all collections instead of the entire database
    assert (
        "test" in deps_backend_database_name.lower()
    ), "Backend database name must contain 'test'"

    if client._db_client._closed is True:
        client = ensure_client(url=db_url, with_indexes=False)

    logger.debug(f"Dropping all collections in database '{deps_backend_database_name}'")
    _collection_names: typing.List[typing.Text] = []
    try:
        _collection_names = client.database.list_collection_names()
    except Exception as e:
        logger.exception(e)
        logger.error(
            f"Error listing collections in database '{deps_backend_database_name}': {e}"
        )
    finally:
        for collection_name in _collection_names:
            try:
                client.database.drop_collection(collection_name)
            except Exception as e:
                logger.exception(e)
                logger.error(
                    f"Error dropping collection '{collection_name}' "
                    + f"in database '{deps_backend_database_name}': {e}"
                )
    logger.info(f"All collections in database '{deps_backend_database_name}' dropped")

    logger.debug(f"Dropping database '{deps_backend_database_name}'")
    try:
        client.database_client.drop_database(deps_backend_database_name)
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error dropping database '{deps_backend_database_name}': {e}")
    logger.info(f"Database '{deps_backend_database_name}' dropped")

    # Close the client
    try:
        client.close()
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error closing client: {e}")


@pytest.fixture(scope="module")
def deps_role_platform_manager(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import PLATFORM_MANAGER_ROLE

    _role = deps_backend_client_session.roles.create(PLATFORM_MANAGER_ROLE)
    logger.info(
        f"Role '{PLATFORM_MANAGER_ROLE.name}' created: {_role.model_dump_json()}"
    )
    return _role


@pytest.fixture(scope="module")
def deps_role_platform_creator(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import PLATFORM_CREATOR_ROLE

    _role = deps_backend_client_session.roles.create(PLATFORM_CREATOR_ROLE)
    logger.info(
        f"Role '{PLATFORM_CREATOR_ROLE.name}' created: {_role.model_dump_json()}"
    )
    return _role


@pytest.fixture(scope="module")
def deps_role_org_owner(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import ORG_OWNER_ROLE

    _role = deps_backend_client_session.roles.create(ORG_OWNER_ROLE)
    logger.info(f"Role '{ORG_OWNER_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_role_org_editor(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import ORG_EDITOR_ROLE

    _role = deps_backend_client_session.roles.create(ORG_EDITOR_ROLE)
    logger.info(f"Role '{ORG_EDITOR_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_role_org_viewer(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import ORG_VIEWER_ROLE

    _role = deps_backend_client_session.roles.create(ORG_VIEWER_ROLE)
    logger.info(f"Role '{ORG_VIEWER_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_role_project_owner(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import PROJECT_OWNER_ROLE

    _role = deps_backend_client_session.roles.create(PROJECT_OWNER_ROLE)
    logger.info(f"Role '{PROJECT_OWNER_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_role_project_editor(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import PROJECT_EDITOR_ROLE

    _role = deps_backend_client_session.roles.create(PROJECT_EDITOR_ROLE)
    logger.info(f"Role '{PROJECT_EDITOR_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_role_project_viewer(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import PROJECT_VIEWER_ROLE

    _role = deps_backend_client_session.roles.create(PROJECT_VIEWER_ROLE)
    logger.info(f"Role '{PROJECT_VIEWER_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_role_na(deps_backend_client_session: "BackendClient"):
    from any_auth.types.role import NA_ROLE

    _role = deps_backend_client_session.roles.create(NA_ROLE)
    logger.info(f"Role '{NA_ROLE.name}' created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def deps_backend_client_session_with_roles(
    deps_backend_client_session: "BackendClient",
    deps_role_platform_manager: "Role",
    deps_role_platform_creator: "Role",
    deps_role_org_owner: "Role",
    deps_role_org_editor: "Role",
    deps_role_org_viewer: "Role",
    deps_role_project_owner: "Role",
    deps_role_project_editor: "Role",
    deps_role_project_viewer: "Role",
    deps_role_na: "Role",
):
    yield deps_backend_client_session


@pytest.fixture(scope="module")
def deps_org(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_org_name: typing.Text,
    deps_fake: Faker,
):
    from any_auth.types.organization import OrganizationCreate

    created_org = deps_backend_client_session_with_roles.organizations.create(
        OrganizationCreate.fake(name=deps_org_name, fake=deps_fake)
    )
    logger.info(f"Organization created: {created_org.model_dump_json()}")
    return created_org


@pytest.fixture(scope="module")
def deps_project(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_org: "Organization",
    deps_proj_name: typing.Text,
):
    from any_auth.types.project import ProjectCreate

    created_project = deps_backend_client_session_with_roles.projects.create(
        ProjectCreate.fake(name=deps_proj_name, fake=deps_fake),
        organization_id=deps_org.id,
        created_by="test",
    )
    logger.info(f"Project created: {created_project.model_dump_json()}")
    return created_project


# === Users Dependencies ===
@pytest.fixture(scope="module")
def deps_user_platform_manager(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for an admin user with USER_LIST permission."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User platform manager created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_platform_creator_password(
    deps_fake: Faker,
) -> typing.Text:
    return deps_fake.password()


@pytest.fixture(scope="module")
def deps_user_platform_creator(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_settings: "Settings",
    deps_user_platform_creator_password: typing.Text,
) -> typing.Tuple["UserInDB", typing.Text]:
    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake, password=deps_user_platform_creator_password)
    )
    logger.info(f"User platform creator created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_platform_creator_expired_token(
    deps_user_platform_creator: typing.Tuple["UserInDB", typing.Text],
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for an expired JWT token."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user, _ = deps_user_platform_creator
    # Create a token that expired 1 hour ago
    now = int(time.time())
    expired_time = now - 3600  # 1 hour ago

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user.id,
            expires_at=expired_time,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
            client_id="test_client",
            scope="read write",
        ),
        deps_settings,
    )

    return (user, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_org_owner(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_org: "Organization",
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for an organization owner user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User org owner created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_org_editor(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_org: "Organization",
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for an organization editor user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User org editor created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_org_viewer(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_org: "Organization",
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for an organization viewer user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User org viewer created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_project_owner(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_project: "Project",
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for a project owner user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User project owner created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_project_editor(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_project: "Project",
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for a project editor user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User project editor created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_project_viewer(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_project: "Project",
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for a project viewer user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User project viewer created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


@pytest.fixture(scope="module")
def deps_user_newbie(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_fake: Faker,
    deps_settings: "Settings",
) -> typing.Tuple["UserInDB", typing.Text]:
    """Fixture for a newbie user."""

    from any_auth.types.oauth2 import OAuth2Token
    from any_auth.types.user import UserCreate
    from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
    from any_auth.utils.oauth2 import generate_refresh_token, generate_token

    user_in_db = deps_backend_client_session_with_roles.users.create(
        UserCreate.fake(fake=deps_fake)
    )
    logger.info(f"User newbie created: {user_in_db.model_dump_json()}")

    oauth2_token = convert_oauth2_token_to_jwt(
        OAuth2Token(
            user_id=user_in_db.id,
            client_id="test_client",
            scope="read write",
            expires_at=int(time.time()) + 3600,
            access_token=generate_token(),
            refresh_token=generate_refresh_token(),
        ),
        deps_settings,
    )
    return (user_in_db, oauth2_token.access_token)


# === End of Users Dependencies ===


# === Role Assignments Dependencies ===
@pytest.fixture(scope="module")
def deps_role_assignment_platform_manager(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_platform_manager: typing.Tuple["UserInDB", typing.Text],
) -> "RoleAssignment":
    from any_auth.types.role import PLATFORM_MANAGER_ROLE
    from any_auth.types.role_assignment import PLATFORM_ID

    user_in_db, _ = deps_user_platform_manager

    # Assign the role to the user on the platform resource
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=PLATFORM_MANAGER_ROLE.name,
        resource_id=PLATFORM_ID,
    )
    logger.info(
        f"Role '{PLATFORM_MANAGER_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_platform_creator(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_platform_creator: typing.Tuple["UserInDB", typing.Text],
) -> "RoleAssignment":
    from any_auth.types.role import PLATFORM_CREATOR_ROLE
    from any_auth.types.role_assignment import PLATFORM_ID

    user_in_db, _ = deps_user_platform_creator

    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=PLATFORM_CREATOR_ROLE.name,
        resource_id=PLATFORM_ID,
    )
    logger.info(
        f"Role '{PLATFORM_CREATOR_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_org_owner(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_org_owner: typing.Tuple["UserInDB", typing.Text],
    deps_org: "Organization",
) -> "RoleAssignment":
    from any_auth.types.role import ORG_OWNER_ROLE

    user_in_db, _ = deps_user_org_owner

    # Assign the organization owner role to the user
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=ORG_OWNER_ROLE.name,
        resource_id=deps_org.id,
    )
    logger.info(
        f"Role '{ORG_OWNER_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_org_editor(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_org_editor: typing.Tuple["UserInDB", typing.Text],
    deps_org: "Organization",
) -> "RoleAssignment":
    from any_auth.types.role import ORG_EDITOR_ROLE

    user_in_db, _ = deps_user_org_editor

    # Assign the organization editor role to the user
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=ORG_EDITOR_ROLE.name,
        resource_id=deps_org.id,
    )
    logger.info(
        f"Role '{ORG_EDITOR_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_org_viewer(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_org_viewer: typing.Tuple["UserInDB", typing.Text],
    deps_org: "Organization",
) -> "RoleAssignment":
    from any_auth.types.role import ORG_VIEWER_ROLE

    user_in_db, _ = deps_user_org_viewer

    # Assign the organization viewer role to the user
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=ORG_VIEWER_ROLE.name,
        resource_id=deps_org.id,
    )
    logger.info(
        f"Role '{ORG_VIEWER_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_project_owner(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_project_owner: typing.Tuple["UserInDB", typing.Text],
    deps_project: "Project",
) -> "RoleAssignment":
    from any_auth.types.role import PROJECT_OWNER_ROLE

    user_in_db, _ = deps_user_project_owner

    # Assign the project owner role to the user
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=PROJECT_OWNER_ROLE.name,
        resource_id=deps_project.id,
    )
    logger.info(
        f"Role '{PROJECT_OWNER_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_project_editor(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_project_editor: typing.Tuple["UserInDB", typing.Text],
    deps_project: "Project",
) -> "RoleAssignment":
    from any_auth.types.role import PROJECT_EDITOR_ROLE

    user_in_db, _ = deps_user_project_editor

    # Assign the project editor role to the user
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=PROJECT_EDITOR_ROLE.name,
        resource_id=deps_project.id,
    )
    logger.info(
        f"Role '{PROJECT_EDITOR_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


@pytest.fixture(scope="module")
def deps_role_assignment_project_viewer(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_project_viewer: typing.Tuple["UserInDB", typing.Text],
    deps_project: "Project",
) -> "RoleAssignment":
    from any_auth.types.role import PROJECT_VIEWER_ROLE

    user_in_db, _ = deps_user_project_viewer

    # Assign the project viewer role to the user
    rs = user_in_db.ensure_role_assignment(
        deps_backend_client_session_with_roles,
        role_name_or_id=PROJECT_VIEWER_ROLE.name,
        resource_id=deps_project.id,
    )
    logger.info(
        f"Role '{PROJECT_VIEWER_ROLE.name}' assignment to "
        + f"user '{user_in_db.username}' created: {rs.model_dump_json()}"
    )

    return rs


# === End of Role Assignments Dependencies ===


# === Members Dependencies ===
@pytest.fixture(scope="module")
def deps_org_member_of_org_owner(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_org_owner: typing.Tuple["UserInDB", typing.Text],
    deps_org: "Organization",
) -> "OrganizationMember":
    from any_auth.types.organization_member import OrganizationMemberCreate

    user_in_db, _ = deps_user_org_owner

    # Joining user as member to the organization
    member = deps_backend_client_session_with_roles.organization_members.create(
        OrganizationMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        organization_id=deps_org.id,
    )
    logger.info(f"User org member created: {member.model_dump_json()}")

    return member


@pytest.fixture(scope="module")
def deps_org_member_of_org_editor(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_org_editor: typing.Tuple["UserInDB", typing.Text],
    deps_org: "Organization",
) -> "OrganizationMember":
    from any_auth.types.organization_member import OrganizationMemberCreate

    user_in_db, _ = deps_user_org_editor

    # Joining user as member to the organization
    member = deps_backend_client_session_with_roles.organization_members.create(
        OrganizationMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        organization_id=deps_org.id,
    )
    logger.info(f"User org member created: {member.model_dump_json()}")

    return member


@pytest.fixture(scope="module")
def deps_org_member_of_org_viewer(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_org_viewer: typing.Tuple["UserInDB", typing.Text],
    deps_org: "Organization",
) -> "OrganizationMember":
    from any_auth.types.organization_member import OrganizationMemberCreate

    user_in_db, _ = deps_user_org_viewer

    # Joining user as member to the organization
    member = deps_backend_client_session_with_roles.organization_members.create(
        OrganizationMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        organization_id=deps_org.id,
    )
    logger.info(f"User org member created: {member.model_dump_json()}")

    return member


@pytest.fixture(scope="module")
def deps_project_member_of_project_owner(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_project_owner: typing.Tuple["UserInDB", typing.Text],
    deps_project: "Project",
) -> "ProjectMember":
    from any_auth.types.project_member import ProjectMemberCreate

    user_in_db, _ = deps_user_project_owner

    # Joining user as member to the project
    _project_member = deps_backend_client_session_with_roles.project_members.create(
        ProjectMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        project_id=deps_project.id,
    )
    logger.info(f"Project member created: {_project_member}")

    return _project_member


@pytest.fixture(scope="module")
def deps_project_member_of_project_editor(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_project_editor: typing.Tuple["UserInDB", typing.Text],
    deps_project: "Project",
) -> "ProjectMember":
    from any_auth.types.project_member import ProjectMemberCreate

    user_in_db, _ = deps_user_project_editor

    # Joining user as member to the project
    _project_member = deps_backend_client_session_with_roles.project_members.create(
        ProjectMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        project_id=deps_project.id,
    )
    logger.info(f"User project member created: {_project_member}")

    return _project_member


@pytest.fixture(scope="module")
def deps_project_member_of_project_viewer(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_user_project_viewer: typing.Tuple["UserInDB", typing.Text],
    deps_project: "Project",
) -> "ProjectMember":
    from any_auth.types.project_member import ProjectMemberCreate

    user_in_db, _ = deps_user_project_viewer

    # Joining user as member to the project
    _project_member = deps_backend_client_session_with_roles.project_members.create(
        ProjectMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        project_id=deps_project.id,
    )
    logger.info(f"User project member created: {_project_member}")

    return _project_member


# === End of Members Dependencies ===


# === OAuth Clients Dependencies ===
@pytest.fixture(scope="module")
def deps_oauth_clients(
    deps_backend_client_session: "BackendClient",
):
    from any_auth.types.oauth_client import OAuthClientCreate

    client_create = OAuthClientCreate.model_validate(
        {
            "name": "Test Client",
            "redirect_uris": ["http://localhost:8000/callback"],
            "client_type": "confidential",
            "allowed_grant_types": ["password", "refresh_token", "authorization_code"],
            "allowed_response_types": ["code", "token"],
            "allowed_scopes": ["openid", "email", "profile"],
        }
    )

    client = deps_backend_client_session.oauth_clients.create(
        client_create, client_id="test_client"
    )

    return client


# === End of OAuth Clients Dependencies ===


@pytest.fixture(scope="module")
def deps_backend_client_session_with_all_resources(
    deps_backend_client_session_with_roles: "BackendClient",
    deps_role_platform_manager: "Role",
    deps_role_platform_creator: "Role",
    deps_role_org_owner: "Role",
    deps_role_org_editor: "Role",
    deps_role_org_viewer: "Role",
    deps_role_project_owner: "Role",
    deps_role_project_editor: "Role",
    deps_role_project_viewer: "Role",
    deps_role_na: "Role",
    deps_org: "Organization",
    deps_project: "Project",
    deps_user_platform_manager: "UserInDB",
    deps_user_platform_creator: "UserInDB",
    deps_user_org_owner: "UserInDB",
    deps_user_org_editor: "UserInDB",
    deps_user_org_viewer: "UserInDB",
    deps_user_project_owner: "UserInDB",
    deps_user_project_editor: "UserInDB",
    deps_user_project_viewer: "UserInDB",
    deps_user_newbie: "UserInDB",
    deps_role_assignment_platform_manager: "RoleAssignment",
    deps_role_assignment_platform_creator: "RoleAssignment",
    deps_role_assignment_org_owner: "RoleAssignment",
    deps_role_assignment_org_editor: "RoleAssignment",
    deps_role_assignment_org_viewer: "RoleAssignment",
    deps_role_assignment_project_owner: "RoleAssignment",
    deps_role_assignment_project_editor: "RoleAssignment",
    deps_role_assignment_project_viewer: "RoleAssignment",
    deps_org_member_of_org_owner: "OrganizationMember",
    deps_org_member_of_org_editor: "OrganizationMember",
    deps_org_member_of_org_viewer: "OrganizationMember",
    deps_project_member_of_project_owner: "ProjectMember",
    deps_project_member_of_project_editor: "ProjectMember",
    deps_project_member_of_project_viewer: "ProjectMember",
    deps_oauth_clients: "OAuthClient",
):
    yield deps_backend_client_session_with_roles


# === API Client Dependencies ===


@pytest.fixture(scope="module")
def test_api_client(
    deps_backend_client_session_with_all_resources: "BackendClient",
    deps_settings: "Settings",
):
    """
    Module-scoped TestClient fixture that uses the module-scoped database session.
    """

    from fastapi.testclient import TestClient

    from any_auth.build_app import build_app

    if not deps_backend_client_session_with_all_resources:
        raise ValueError("Backend client session is not provided")

    deps_settings.probe_required_environment_variables()

    app = build_app(
        settings=deps_settings,
        backend_client=deps_backend_client_session_with_all_resources,
    )

    with TestClient(app) as client:
        yield client


# === End of API Client Dependencies ===


# === Utils ===
def _new_db_client(db_url: httpx.URL) -> pymongo.MongoClient:
    db_client = pymongo.MongoClient(str(db_url))
    logger.info(
        f"Connecting to '{str(db_url.copy_with(username=None, password=None, query=None))}'"  # noqa: E501
    )
    return db_client


def _validate_db_client(db_client: pymongo.MongoClient) -> pymongo.MongoClient:
    ping_result = db_client.admin.command("ping")
    logger.info(f"Ping result: {ping_result}")
    assert ping_result["ok"] == 1
    return db_client


def _init_backend_client(
    db_client: pymongo.MongoClient,
    *,
    settings: "Settings",
    backend_database_name: typing.Text,
    with_indexes: bool = True,
) -> "BackendClient":
    from any_auth.backend import BackendClient, BackendSettings

    logger.info(f"Connecting to '{backend_database_name}'")

    client = BackendClient.from_settings(
        settings,
        backend_settings=BackendSettings.from_any_auth_settings(
            settings, database_name=backend_database_name
        ),
    )

    client.touch(with_indexes=with_indexes)
    client.database.list_collection_names()

    logger.info(f"Ensured database '{backend_database_name}' created")
    return client


# === End of Utils ===
