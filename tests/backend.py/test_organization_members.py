import pytest
from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.organization import OrganizationCreate
from any_auth.types.organization_member import OrganizationMemberCreate
from any_auth.types.user import UserCreate

fake = Faker()


def test_organization_members_indexes(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
):
    """
    Ensure indexes are created without error.
    """
    backend_client_session.organization_members.create_indexes()


@pytest.fixture
def org_user_membership(
    raise_if_not_test_env: None,
    backend_client_session: BackendClient,
):
    """
    Create a test organization, a test user, and return (org_id, user_id).
    """
    # Create user
    user_create = UserCreate(
        username=fake.user_name(),
        full_name=fake.name(),
        email=fake.email(),
        phone=fake.phone_number(),
        password=fake.password(),
        metadata={"test": "organization-members"},
    )
    user = backend_client_session.users.create(user_create)

    # Create organization
    org_create = OrganizationCreate(
        name=fake.user_name(),
        full_name=fake.company(),
        metadata={"test": "organization-members"},
    )
    org = backend_client_session.organizations.create(org_create)

    yield (org.id, user.id)


def test_organization_members_crud(
    org_user_membership,
    backend_client_session: BackendClient,
):
    """
    Test create, retrieve, list, and delete for organization members.
    """
    org_id, user_id = org_user_membership

    # 1. List members (should be empty initially)
    members_page = (
        backend_client_session.organization_members.retrieve_by_organization_id(org_id)
    )
    assert len(members_page) == 0

    # 2. Create a member
    member_create = OrganizationMemberCreate(
        user_id=user_id,
        metadata={"role": "tester"},
    )
    member = backend_client_session.organization_members.create(
        member_create, organization_id=org_id
    )
    assert member is not None
    assert member.user_id == user_id
    assert member.organization_id == org_id
    assert member.metadata["role"] == "tester"

    # 3. Retrieve by member_id
    retrieved = backend_client_session.organization_members.retrieve(member.id)
    assert retrieved is not None
    assert retrieved.id == member.id

    # 4. List members again (should have 1)
    members_page = (
        backend_client_session.organization_members.retrieve_by_organization_id(org_id)
    )
    assert len(members_page) == 1

    # 5. Disable member
    disabled_member = backend_client_session.organization_members.disable(member.id)
    assert disabled_member.disabled is True

    # 6. Enable member
    enabled_member = backend_client_session.organization_members.enable(member.id)
    assert enabled_member.disabled is False

    # 7. Delete member
    backend_client_session.organization_members.delete(member.id)
    members_page = (
        backend_client_session.organization_members.retrieve_by_organization_id(org_id)
    )
    assert len(members_page) == 0
