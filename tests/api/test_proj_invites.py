import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.invite import Invite, InviteCreate, InviteInDB
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember
from any_auth.types.user import UserCreate, UserInDB
from any_auth.utils.jwt_manager import create_jwt_token


def test_api_project_invites_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_fake: Faker,
    deps_settings: Settings,
):
    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
    ]:
        # Prepare a new user to be invited
        new_user = backend_client.users.create(UserCreate.fake(fake=deps_fake))
        new_user_token = create_jwt_token(
            new_user.id,
            jwt_secret=deps_settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=deps_settings.JWT_ALGORITHM,
        )

        # Create the invite
        headers = {"Authorization": f"Bearer {token}"}
        response = test_api_client.post(
            f"/projects/{project_id}/invites",
            headers=headers,
            params={"use_smtp": False},
            json=InviteCreate.model_validate(
                {"email": new_user.email, "metadata": {"role": "viewer"}}
            ).model_dump(exclude_none=True),
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        created_invite = InviteInDB.model_validate(response.json())
        assert created_invite is not None

        # Check that the invite was created
        headers = {"Authorization": f"Bearer {deps_user_project_owner[1]}"}
        response = test_api_client.get(
            f"/projects/{project_id}/invites",
            headers=headers,
        )
        assert response.status_code == 200
        page_invites = Page[Invite].model_validate(response.json())
        assert len(page_invites.data) == 1
        assert page_invites.data[0].email == new_user.email
        assert page_invites.data[0].resource_id == project_id
        assert page_invites.data[0].invited_by == user.id

        # Accept the invite
        headers = {"Authorization": f"Bearer {new_user_token}"}
        response = test_api_client.post(
            f"/projects/{project_id}/accept-invite",
            headers=headers,
            params={"token": created_invite.temporary_token},
        )
        assert response.status_code == 200
        new_project_member = ProjectMember.model_validate(response.json())
        assert new_project_member is not None
        assert new_project_member.user_id == new_user.id
        assert new_project_member.project_id == project_id


def test_api_project_invites_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        # Create a new user to be invited
        new_user = backend_client.users.create(UserCreate.fake(fake=deps_fake))

        # Create the invite
        headers = {"Authorization": f"Bearer {token}"}
        response = test_api_client.post(
            f"/projects/{project_id}/invites",
            headers=headers,
            params={"use_smtp": False},
            json=InviteCreate.model_validate(
                {"email": new_user.email, "metadata": {"role": "viewer"}}
            ).model_dump(exclude_none=True),
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
