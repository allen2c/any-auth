import pytest
from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.organization import OrganizationCreate
from any_auth.types.project import ProjectCreate
from any_auth.types.project_member import ProjectMemberCreate
from any_auth.types.user import UserCreate

fake = Faker()


def test_project_members_indexes(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
):
    """
    Ensure indexes are created without error.
    """
    backend_client_session.project_members.create_indexes()


@pytest.fixture
def project_user_membership(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
):
    """
    Create a test organization, a test project, and a test user, then return (project_id, user_id).
    """  # noqa: E501

    # Create user
    user_create = UserCreate(
        username=fake.user_name(),
        full_name=fake.name(),
        email=fake.email(),
        phone=fake.phone_number(),
        password=fake.password(),
        metadata={"test": "project-members"},
    )
    user = backend_client_session.users.create(user_create)

    # Create organization
    org_create = OrganizationCreate(
        name=fake.user_name(),
        full_name=fake.company(),
        metadata={"test": "project-members"},
    )
    org = backend_client_session.organizations.create(org_create)

    # Create project
    project_create = ProjectCreate(
        name=fake.user_name(),
        full_name=fake.catch_phrase(),
        metadata={"test": "project-members"},
    )
    project = backend_client_session.projects.create(
        project_create, organization_id=org.id, created_by=user.id
    )

    yield (project.id, user.id)


def test_project_members_crud(
    project_user_membership,
    backend_client_session: BackendClient,
):
    """
    Test create, retrieve, list, and delete for project members.
    """
    project_id, user_id = project_user_membership

    # 1. List members (should be empty initially)
    members_page = backend_client_session.project_members.retrieve_by_project_id(
        project_id
    )
    assert len(members_page) == 0

    # 2. Create a member
    member_create = ProjectMemberCreate(
        user_id=user_id,
        metadata={"role": "developer"},
    )
    member = backend_client_session.project_members.create(
        member_create, project_id=project_id
    )
    assert member is not None
    assert member.user_id == user_id
    assert member.project_id == project_id
    assert member.metadata["role"] == "developer"

    # 3. Retrieve by member_id
    retrieved = backend_client_session.project_members.retrieve(member.id)
    assert retrieved is not None
    assert retrieved.id == member.id

    # 4. List members again (should have 1)
    members_page = backend_client_session.project_members.retrieve_by_project_id(
        project_id
    )
    assert len(members_page) == 1

    # 5. Disable member
    disabled_member = backend_client_session.project_members.disable(member.id)
    assert disabled_member.disabled is True

    # 6. Enable member
    enabled_member = backend_client_session.project_members.enable(member.id)
    assert enabled_member.disabled is False

    # 7. Delete member
    backend_client_session.project_members.delete(member.id)
    members_page = backend_client_session.project_members.retrieve_by_project_id(
        project_id
    )
    assert len(members_page) == 0
