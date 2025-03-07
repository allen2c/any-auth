import typing

from any_auth.backend import BackendClient
from any_auth.types.organization import Organization
from any_auth.types.organization_member import OrganizationMemberCreate
from any_auth.types.user import UserInDB


def test_organization_members_crud(
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_org: Organization,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test create, retrieve, list, and delete for organization members.
    """

    newbie_user, newbie_token = deps_user_newbie

    # 1. List members (should be empty initially)
    members = deps_backend_client_session_with_all_resources.organization_members.retrieve_by_organization_id(  # noqa: E501
        deps_org.id
    )
    assert len(members) == 0

    # 2. Create a member
    member_create = OrganizationMemberCreate(
        user_id=newbie_user.id,
        metadata={"role": "tester"},
    )
    member = deps_backend_client_session_with_all_resources.organization_members.create(
        member_create, organization_id=deps_org.id
    )
    assert member is not None
    assert member.user_id == newbie_user.id
    assert member.organization_id == deps_org.id
    assert member.metadata["role"] == "tester"

    # 3. Retrieve by member_id
    retrieved = (
        deps_backend_client_session_with_all_resources.organization_members.retrieve(
            member.id
        )
    )
    assert retrieved is not None
    assert retrieved.id == member.id

    # 4. List members again (should have 1)
    new_members = deps_backend_client_session_with_all_resources.organization_members.retrieve_by_organization_id(  # noqa: E501
        deps_org.id
    )
    assert len(new_members) == len(members) + 1

    # 5. Delete member
    deps_backend_client_session_with_all_resources.organization_members.delete(
        member.id
    )
    new_members = deps_backend_client_session_with_all_resources.organization_members.retrieve_by_organization_id(  # noqa: E501
        deps_org.id
    )
    assert len(new_members) == len(members)
