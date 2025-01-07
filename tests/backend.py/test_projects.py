import pprint
import typing

import pytest
from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.organization import Organization, OrganizationCreate
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.user import UserCreate, UserInDB

fake = Faker()

USERNAME = fake.user_name()
ORGANIZATION_NAME = fake.user_name()

PROJECTS_CREATE = 3


@pytest.fixture
def user_org(
    fake: Faker,
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
) -> typing.Tuple[UserInDB, Organization]:
    # Create indexes
    backend_client_session.users.create_indexes()
    backend_client_session.organizations.create_indexes()
    backend_client_session.projects.create_indexes()

    # Create user if not exists
    user = backend_client_session.users.retrieve_by_username(USERNAME)
    if user is None:
        user_create = UserCreate(
            username=USERNAME,
            full_name=fake.name(),
            email=fake.email(),
            phone=fake.phone_number(),
            password=fake.password(),
            metadata={"test": "test"},
        )
        user = backend_client_session.users.create(user_create)
    assert user is not None

    # Create organization if not exists
    organization = backend_client_session.organizations.retrieve_by_name(
        ORGANIZATION_NAME
    )
    if organization is None:
        organization_create = OrganizationCreate(
            name=ORGANIZATION_NAME,
            full_name=fake.name(),
            metadata={"test": "test"},
        )
        organization = backend_client_session.organizations.create(organization_create)
    assert organization is not None

    return (user, organization)


def test_projects_create(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
    fake: Faker,
    user_org: typing.Tuple[UserInDB, Organization],
):
    user, organization = user_org

    # Create projects
    page_projects = backend_client_session.projects.list(
        organization_id=organization.id
    )
    assert len(page_projects.data) == 0

    projects_create = [
        ProjectCreate(
            name=fake.user_name(),
            full_name=fake.name(),
            metadata={"test": "test"},
        )
        for _ in range(PROJECTS_CREATE)
    ]

    for project_create in projects_create:
        assert (
            backend_client_session.projects.create(
                project_create, organization_id=organization.id, created_by=user.id
            )
            is not None
        )


def test_projects_get(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
    user_org: typing.Tuple[UserInDB, Organization],
):
    user, organization = user_org

    # Get all projects
    has_more = True
    after: typing.Text | None = None
    projects: typing.List[Project] = []
    limit = 1
    while has_more:
        page_projects = backend_client_session.projects.list(
            organization_id=organization.id, after=after, limit=limit
        )
        has_more = page_projects.has_more
        after = page_projects.last_id
        assert len(page_projects.data) == limit
        projects.extend(page_projects.data)
    assert len(projects) == PROJECTS_CREATE

    # Get project by id
    project_id = projects[0].id
    project = backend_client_session.projects.retrieve(project_id)
    assert project is not None
    assert project.id == project_id

    # Get project by name
    project_name = projects[0].name
    project = backend_client_session.projects.retrieve_by_name(project_name)
    assert project is not None
    assert project.name == project_name


def test_projects_update(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
    fake: Faker,
    user_org: typing.Tuple[UserInDB, Organization],
):
    user, organization = user_org

    # Get all projects
    projects = backend_client_session.projects.list(organization_id=organization.id)
    assert len(projects.data) == PROJECTS_CREATE
    project = projects.data[0]

    # Update project
    project_update = ProjectUpdate(
        full_name=fake.name(),
        metadata={"test": "test2"},
    )
    updated_project = backend_client_session.projects.update(project.id, project_update)
    assert updated_project is not None
    assert updated_project.id == project.id
    assert updated_project.full_name == project_update.full_name
    assert pprint.pformat(updated_project.metadata) == pprint.pformat(
        project_update.metadata
    )


def test_projects_disable(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
    user_org: typing.Tuple[UserInDB, Organization],
):
    user, organization = user_org

    # Get all projects
    projects = backend_client_session.projects.list(organization_id=organization.id)
    assert len(projects.data) == PROJECTS_CREATE
    project = projects.data[0]
    assert project.disabled is False

    # Disable project
    disabled_project = backend_client_session.projects.set_disabled(
        project.id, disabled=True
    )
    assert disabled_project.disabled is True

    # Enable project
    enabled_project = backend_client_session.projects.set_disabled(
        project.id, disabled=False
    )
    assert enabled_project.disabled is False
