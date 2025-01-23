import random
import typing

from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.organization import OrganizationCreate
from any_auth.types.project import ProjectCreate
from any_auth.types.role import PLATFORM_ROLES, TENANT_ROLES, Role
from any_auth.types.user import UserCreate


def test_role_assignments_indexes(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    backend_client_session.users.create_indexes()
    backend_client_session.projects.create_indexes()
    backend_client_session.roles.create_indexes()
    backend_client_session.role_assignments.create_indexes()


def test_role_assignments_operations(
    raise_if_not_test_env: None, backend_client_session: BackendClient
):
    # Create a user
    user = backend_client_session.users.create(
        UserCreate(
            username=Settings.fake.user_name(),
            full_name=Settings.fake.name(),
            email=Settings.fake.email(),
            phone=Settings.fake.phone_number(),
            password=Settings.fake.password(),
            metadata={"test": "test"},
        )
    )
    assert user is not None

    # Create a organization
    organization = backend_client_session.organizations.create(
        OrganizationCreate(
            name=Settings.fake.user_name(),
            full_name="default",
            metadata={"test": "test"},
        )
    )
    assert organization is not None

    # Create a project
    project = backend_client_session.projects.create(
        ProjectCreate(
            name=Settings.fake.user_name(),
            full_name="default",
            metadata={"test": "test"},
        ),
        organization_id=organization.id,
        created_by=user.id,
    )
    assert project is not None

    # Create all roles
    _all_roles = PLATFORM_ROLES + TENANT_ROLES
    roles: typing.List[Role] = []
    for role_create in _all_roles:
        role = backend_client_session.roles.create(role_create)
        assert role is not None
        roles.append(role)
    assert backend_client_session.roles.retrieve(roles[0].id) is not None
    assert (
        len(
            backend_client_session.roles.retrieve_by_ids(
                [role.id for role in roles[:2]]
            )
        )
        > 0
    )
    assert backend_client_session.roles.retrieve_by_name(roles[0].name) is not None

    # Assign roles to the user
    _sampled_assigned_roles = random.sample(roles, k=max(1, len(roles) // 10))
    for role in _sampled_assigned_roles:
        backend_client_session.role_assignments.assign_role(
            user_id=user.id, role_id=role.id, project_id=project.id
        )

    # Get the role assignments
    role_assignments = backend_client_session.role_assignments.retrieve_by_user_id(
        user_id=user.id, project_id=project.id
    )
    assert len(role_assignments) == len(_sampled_assigned_roles)

    # Delete the role assignments
    for role_assignment in role_assignments:
        backend_client_session.role_assignments.delete(role_assignment.id)

    # Check that the role assignments are deleted
    assert (
        len(
            backend_client_session.role_assignments.retrieve_by_user_id(
                user_id=user.id, project_id=project.id
            )
        )
        == 0
    )
