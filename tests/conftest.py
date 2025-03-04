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

from any_auth import LOGGER_NAME
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.organization import Organization, OrganizationCreate
from any_auth.types.organization_member import OrganizationMemberCreate
from any_auth.types.project import Project, ProjectCreate
from any_auth.types.project_member import ProjectMemberCreate
from any_auth.types.role import (
    NA_ROLE,
    ORG_EDITOR_ROLE,
    ORG_OWNER_ROLE,
    ORG_VIEWER_ROLE,
    PLATFORM_CREATOR_ROLE,
    PLATFORM_MANAGER_ROLE,
    PROJECT_EDITOR_ROLE,
    PROJECT_OWNER_ROLE,
    PROJECT_VIEWER_ROLE,
    Role,
)
from any_auth.types.user import UserCreate, UserInDB
from any_auth.utils.jwt_manager import create_jwt_token

set_logger("tests")
set_logger(LOGGER_NAME)

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "true")
    monkeypatch.setenv("IS_TEST", "true")
    monkeypatch.setenv("IS_TESTING", "true")
    monkeypatch.setenv("PYTEST_RUNNING", "true")


@pytest.fixture
def raise_if_not_test_env():
    from any_auth.config import Settings

    settings = Settings()  # type: ignore

    assert os.getenv("IS_TESTING") == "true"
    assert settings.ENVIRONMENT == "test"


@pytest.fixture(scope="module")
def fake():
    from faker import Faker

    return Faker()


@pytest.fixture(scope="module")
def backend_database_name():
    return f"auth_test_{int(time.time())}_{str(uuid.uuid4())[:8]}"


@pytest.fixture(scope="module")
def organization_name(fake: Faker):
    return f"org_{fake.user_name()}"


@pytest.fixture(scope="module")
def project_name(fake: Faker):
    return f"project_{fake.user_name()}"


@pytest.fixture(scope="module")
def backend_client_session(backend_database_name):
    from any_auth.backend import BackendClient, BackendSettings
    from any_auth.config import Settings

    settings = Settings()  # type: ignore

    db_url = httpx.URL(settings.DATABASE_URL.get_secret_value())

    def new_db_client() -> pymongo.MongoClient:
        hidden_db_url = db_url.copy_with(username=None, password=None, query=None)
        db_client = pymongo.MongoClient(str(db_url))
        logger.info(f"Connecting to '{str(hidden_db_url)}'")
        ping_result = db_client.admin.command("ping")
        logger.info(f"Ping result: {ping_result}")
        assert ping_result["ok"] == 1
        return db_client

    def ensure_client(
        db_client: pymongo.MongoClient, backend_database_name: typing.Text
    ) -> BackendClient:
        logger.info(f"Connecting to '{backend_database_name}'")

        client = BackendClient.from_settings(
            settings,
            backend_settings=BackendSettings.from_any_auth_settings(
                settings, database_name=backend_database_name
            ),
        )
        client = BackendClient(
            db_client=db_client,
            settings=BackendSettings(database=backend_database_name),
        )
        client.database.list_collection_names()
        logger.info(f"Ensured database '{backend_database_name}' created")
        return client

    client = ensure_client(new_db_client(), backend_database_name)

    yield client

    # Teardown: Drop all collections instead of the entire database
    if client._db_client._closed is True:
        client = ensure_client(new_db_client(), backend_database_name)
    for collection_name in client.database.list_collection_names():
        client.database.drop_collection(collection_name)
    logger.info(f"All collections in database '{backend_database_name}' dropped")

    # Close the client
    client.close()


@pytest.fixture(scope="module")
def role_platform_manager(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(PLATFORM_MANAGER_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_platform_creator(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(PLATFORM_CREATOR_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_org_owner(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(ORG_OWNER_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_org_editor(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(ORG_EDITOR_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_org_viewer(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(ORG_VIEWER_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_project_owner(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(PROJECT_OWNER_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_project_editor(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(PROJECT_EDITOR_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_project_viewer(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(PROJECT_VIEWER_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def role_na(backend_client_session: "BackendClient"):
    _role = backend_client_session.roles.create(NA_ROLE)
    logger.info(f"Role created: {_role.model_dump_json()}")
    return _role


@pytest.fixture(scope="module")
def backend_client_session_with_roles(
    backend_client_session: "BackendClient",
    role_platform_manager: Role,
    role_platform_creator: Role,
    role_org_owner: Role,
    role_org_editor: Role,
    role_org_viewer: Role,
    role_project_owner: Role,
    role_project_editor: Role,
    role_project_viewer: Role,
    role_na: Role,
):
    yield backend_client_session


@pytest.fixture(scope="module")
def org_of_session(backend_client_session_with_roles: "BackendClient", fake: Faker):
    created_org = backend_client_session_with_roles.organizations.create(
        OrganizationCreate.fake(fake)
    )
    logger.info(f"Organization created: {created_org.model_dump_json()}")
    return created_org


@pytest.fixture(scope="module")
def project_of_session(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    org_of_session: Organization,
):
    created_project = backend_client_session_with_roles.projects.create(
        ProjectCreate.fake(fake),
        organization_id=org_of_session.id,
        created_by="test",
    )
    logger.info(f"Project created: {created_project.model_dump_json()}")
    return created_project


@pytest.fixture(scope="module")
def test_client_module(backend_client_session_with_roles: "BackendClient"):
    """
    Module-scoped TestClient fixture that uses the module-scoped database session.
    """

    from fastapi.testclient import TestClient

    from any_auth.build_app import build_app
    from any_auth.config import Settings

    if not backend_client_session:
        raise ValueError("Backend client session is not provided")

    Settings.probe_required_environment_variables()

    app_settings = Settings()  # type: ignore
    app = build_app(
        settings=app_settings, backend_client=backend_client_session_with_roles
    )

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def user_platform_manager(
    backend_client_session_with_roles: "BackendClient", fake: Faker
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for an admin user with USER_LIST permission."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User platform manager created: {user_in_db.model_dump_json()}")
    # Assign the role to the user on the platform resource
    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=PLATFORM_MANAGER_ROLE.name,
        resource_id="platform",
    )
    logger.info(f"User platform manager created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_platform_creator(
    backend_client_session_with_roles: "BackendClient", fake: Faker
) -> typing.Tuple[UserInDB, typing.Text]:
    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User platform creator created: {user_in_db.model_dump_json()}")

    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=PLATFORM_CREATOR_ROLE.name,
        resource_id="platform",
    )
    logger.info(f"User platform creator created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_org_owner(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    org_of_session: Organization,
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for an organization owner user."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User org owner created: {user_in_db.model_dump_json()}")

    # Joining user as member to the organization
    backend_client_session_with_roles.organization_members.create(
        OrganizationMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        organization_id=org_of_session.id,
    )
    logger.info(f"User org owner created: {user_in_db.model_dump_json()}")

    # Assign the organization owner role to the user
    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=ORG_OWNER_ROLE.name,
        resource_id=org_of_session.id,
    )
    logger.info(f"User org owner created: {user_in_db.model_dump_json()}")
    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_org_editor(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    org_of_session: Organization,
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for an organization editor user."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User org editor created: {user_in_db.model_dump_json()}")

    # Joining user as member to the organization
    backend_client_session_with_roles.organization_members.create(
        OrganizationMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        organization_id=org_of_session.id,
    )
    logger.info(f"User org editor created: {user_in_db.model_dump_json()}")

    # Assign the organization editor role to the user
    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=ORG_EDITOR_ROLE.name,
        resource_id=org_of_session.id,
    )
    logger.info(f"User org editor created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_org_viewer(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    org_of_session: Organization,
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for an organization viewer user."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User org viewer created: {user_in_db.model_dump_json()}")

    # Joining user as member to the organization
    backend_client_session_with_roles.organization_members.create(
        OrganizationMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        organization_id=org_of_session.id,
    )
    logger.info(f"User org viewer created: {user_in_db.model_dump_json()}")

    # Assign the organization viewer role to the user
    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=ORG_VIEWER_ROLE.name,
        resource_id=org_of_session.id,
    )
    logger.info(f"User org viewer created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_project_owner(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    project_of_session: Project,
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for a project owner user."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User project owner created: {user_in_db.model_dump_json()}")

    # Joining user as member to the project
    _project_member = backend_client_session_with_roles.project_members.create(
        ProjectMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        project_id=project_of_session.id,
    )
    logger.info(f"Project member created: {_project_member}")

    # Assign the project owner role to the user
    _role_assignment = user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=PROJECT_OWNER_ROLE.name,
        resource_id=project_of_session.id,
    )
    logger.info(f"Role assigned: {_role_assignment}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_project_editor(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    project_of_session: Project,
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for a project editor user."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User project editor created: {user_in_db.model_dump_json()}")

    # Joining user as member to the project
    backend_client_session_with_roles.project_members.create(
        ProjectMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        project_id=project_of_session.id,
    )
    logger.info(f"User project editor created: {user_in_db.model_dump_json()}")
    # Assign the project editor role to the user
    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=PROJECT_EDITOR_ROLE.name,
        resource_id=project_of_session.id,
    )
    logger.info(f"User project editor created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_project_viewer(
    backend_client_session_with_roles: "BackendClient",
    fake: Faker,
    project_of_session: Project,
) -> typing.Tuple[UserInDB, typing.Text]:
    """Fixture for a project viewer user."""

    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User project viewer created: {user_in_db.model_dump_json()}")

    # Joining user as member to the project
    backend_client_session_with_roles.project_members.create(
        ProjectMemberCreate(user_id=user_in_db.id, metadata={"test": "test"}),
        project_id=project_of_session.id,
    )
    logger.info(f"User project viewer created: {user_in_db.model_dump_json()}")

    # Assign the project viewer role to the user
    user_in_db.ensure_role_assignment(
        backend_client_session_with_roles,
        role_name_or_id=PROJECT_VIEWER_ROLE.name,
        resource_id=project_of_session.id,
    )
    logger.info(f"User project viewer created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)


@pytest.fixture(scope="module")
def user_newbie(
    backend_client_session_with_roles: "BackendClient", fake: Faker
) -> typing.Tuple[UserInDB, typing.Text]:
    user_in_db = backend_client_session_with_roles.users.create(UserCreate.fake(fake))
    logger.info(f"User newbie created: {user_in_db.model_dump_json()}")

    settings = Settings()  # type: ignore
    token = create_jwt_token(
        user_in_db.id,
        jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
        jwt_algorithm=settings.JWT_ALGORITHM,
    )
    return (user_in_db, token)
