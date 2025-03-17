import typing

from any_auth.backend import BackendClient
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMemberCreate
from any_auth.types.user import UserInDB


def test_project_members_crud(
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_project: Project,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test create, retrieve, list, and delete for project members.
    """
    backend_client_session = deps_backend_client_session_with_all_resources

    # 1. List members (should be empty initially)
    original_members = backend_client_session.project_members.retrieve_by_project_id(
        deps_project.id
    )
    assert len(original_members) > 0, "Start with users with role and as member."

    # 2. Create a member
    member_create = ProjectMemberCreate(
        user_id=deps_user_newbie[0].id,
        metadata={"role": "developer"},
    )
    member = backend_client_session.project_members.create(
        member_create, project_id=deps_project.id
    )
    assert member is not None
    assert member.user_id == deps_user_newbie[0].id
    assert member.project_id == deps_project.id
    assert member.metadata["role"] == "developer"

    # 3. Retrieve by member_id
    retrieved = backend_client_session.project_members.retrieve(member.id)
    assert retrieved is not None
    assert retrieved.id == member.id

    # 4. List members again (should have 1)
    members_page = backend_client_session.project_members.retrieve_by_project_id(
        deps_project.id
    )
    assert len(members_page) == len(original_members) + 1

    # 5. Delete member
    backend_client_session.project_members.delete(member.id)
    members_page = backend_client_session.project_members.retrieve_by_project_id(
        deps_project.id
    )
    assert len(members_page) == len(original_members)
