import pprint
import typing

from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.organization import Organization
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.user import UserInDB

fake = Faker()

USERNAME = fake.user_name()
ORGANIZATION_NAME = fake.user_name()

PROJECTS_CREATE = 3


def test_projects_create(
    deps_backend_client_session_with_roles: BackendClient,
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session_with_roles
    user, _ = deps_user_org_editor

    # Create projects
    page_projects = backend_client_session.projects.list(organization_id=deps_org.id)
    assert len(page_projects.data) == 0

    projects_create = [
        ProjectCreate(
            name=deps_fake.user_name(),
            full_name=deps_fake.name(),
            metadata={"test": "test"},
        )
        for _ in range(PROJECTS_CREATE)
    ]

    for project_create in projects_create:
        assert (
            backend_client_session.projects.create(
                project_create, organization_id=deps_org.id, created_by=user.id
            )
            is not None
        )


def test_projects_get(
    deps_backend_client_session_with_roles: BackendClient,
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    backend_client_session = deps_backend_client_session_with_roles
    user, _ = deps_user_org_editor

    # Get all projects
    has_more = True
    after: typing.Text | None = None
    projects: typing.List[Project] = []
    limit = 1
    while has_more:
        page_projects = backend_client_session.projects.list(
            organization_id=deps_org.id, after=after, limit=limit
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
    deps_backend_client_session_with_roles: BackendClient,
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_fake: Faker,
):
    backend_client_session = deps_backend_client_session_with_roles
    user, _ = deps_user_org_editor

    # Get all projects
    projects = backend_client_session.projects.list(organization_id=deps_org.id)
    assert len(projects.data) == PROJECTS_CREATE
    project = projects.data[0]

    # Update project
    project_update = ProjectUpdate(
        full_name=deps_fake.name(),
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
    deps_backend_client_session_with_roles: BackendClient,
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    backend_client_session = deps_backend_client_session_with_roles
    user, _ = deps_user_org_editor

    # Get all projects
    projects = backend_client_session.projects.list(organization_id=deps_org.id)
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
