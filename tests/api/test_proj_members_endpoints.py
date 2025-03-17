import typing

from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate
from any_auth.types.user import UserInDB


def test_api_list_project_members_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
):
    project_id = deps_project.id

    # --- Test Allowed Users ---
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/projects/{project_id}/members",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["object"] == "list"


def test_api_list_project_members_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/projects/{project_id}/members",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_create_project_member_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    project_id = deps_project.id
    user_id = deps_user_newbie[0].id
    _member_create = ProjectMemberCreate(user_id=user_id)

    # --- Test Allowed Users ---
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            f"/projects/{project_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["user_id"] == user_id


def test_api_create_project_member_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
):
    project_id = deps_project.id
    user_id = deps_user_newbie[0].id
    _member_create = ProjectMemberCreate(user_id=user_id)

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            f"/projects/{project_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_retrieve_project_member_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id
    # --- Test Allowed Users ---
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/projects/{project_id}/members/{member_id}",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["id"] == member_id


def test_api_retrieve_project_member_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    # --- Test Denied Users ---
    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/projects/{project_id}/members/{member_id}",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_project_member_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id

    # --- Test Allowed Users ---
    for user, token in [
        deps_user_platform_manager,
        deps_user_project_owner,
    ]:
        # Create a member to delete
        proj_member = backend_client.project_members.create(
            ProjectMemberCreate(user_id=deps_user_newbie[0].id),
            project_id=project_id,
        )

        response = test_api_client.delete(
            f"/projects/{project_id}/members/{proj_member.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_project_member_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.delete(
            f"/projects/{project_id}/members/{member_id}",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
