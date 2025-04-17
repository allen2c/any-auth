import time
import typing

from faker import Faker

from any_auth.backend import BackendClient
from any_auth.types.invite import InviteCreate, InviteInDB

TEST_RESOURCE_ID = "proj_123"
TEST_ACTIVE_USER_ID = "user_456"
TEST_NUM_INVITES = 3


def test_invites_create(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    """Test creating invites."""
    backend_client_session = deps_backend_client_session

    # List invites (should be empty initially)
    page_invites = backend_client_session.invites.list(resource_id=TEST_RESOURCE_ID)
    assert len(page_invites.data) == 0

    for _ in range(TEST_NUM_INVITES):
        # Create an invite
        invite_create = InviteCreate(
            email=deps_fake.email(),
            metadata={"role": "member"},
        )
        invite = backend_client_session.invites.create(
            invite_create,
            resource_id=TEST_RESOURCE_ID,
            invited_by=TEST_ACTIVE_USER_ID,
        )
        assert invite is not None
        assert invite.resource_id == TEST_RESOURCE_ID
        assert invite.invited_by == TEST_ACTIVE_USER_ID
        assert invite.email == invite_create.email
        assert invite.metadata["role"] == "member"
        assert invite.expires_at > int(time.time())
        assert invite.temporary_token is not None


def test_invites_retrieve(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    """Test retrieving invites."""
    backend_client_session = deps_backend_client_session

    # List all invites
    has_more = True
    after: typing.Text | None = None
    invites: typing.List[InviteInDB] = []
    limit = 2
    while has_more:
        page_invites = backend_client_session.invites.list(
            resource_id=TEST_RESOURCE_ID,
            after=after,
            limit=limit,
        )
        has_more = page_invites.has_more
        after = page_invites.last_id
        invites.extend(page_invites.data)

    assert len(invites) >= TEST_NUM_INVITES

    # Retrieve by ID
    retrieved_invite = backend_client_session.invites.retrieve(invites[0].id)
    assert retrieved_invite is not None
    assert retrieved_invite.id == invites[0].id
    assert retrieved_invite.email == invites[0].email
    assert retrieved_invite.resource_id == invites[0].resource_id

    # Retrieve by email and resource ID
    by_email = backend_client_session.invites.retrieve_by_email_and_resource_id(
        invites[0].email, TEST_RESOURCE_ID
    )
    assert by_email is not None
    assert by_email.id == invites[0].id

    # Retrieve by temporary token
    by_token = backend_client_session.invites.retrieve_by_temporary_token(
        invites[0].temporary_token,
        email=invites[0].email,
        resource_id=TEST_RESOURCE_ID,
    )
    assert by_token is not None
    assert by_token.id == invites[0].id


def test_invites_delete(
    deps_backend_client_session: BackendClient,
    deps_fake: Faker,
):
    """Test deleting invites."""
    backend_client_session = deps_backend_client_session

    # Get all invites
    page_invites = backend_client_session.invites.list(resource_id=TEST_RESOURCE_ID)
    assert len(page_invites.data) >= TEST_NUM_INVITES

    # Delete the invite
    backend_client_session.invites.delete(page_invites.data[0].id)

    # Verify it's gone
    retrieved = backend_client_session.invites.retrieve(page_invites.data[0].id)
    assert retrieved is None
