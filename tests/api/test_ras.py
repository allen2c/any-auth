import typing

from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.project import Project
from any_auth.types.role import Role
from any_auth.types.role_assignment import RoleAssignment, RoleAssignmentCreate
from any_auth.types.user import UserInDB


def test_api_create_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_role_platform_creator: "Role",
):
    target_role = deps_role_platform_creator

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        _role_assignment_create = RoleAssignmentCreate(
            target_id=deps_user_newbie[0].id,
            role_id=target_role.id,
            resource_id=deps_project.id,
        )

        response = test_api_client.post(
            "/v1/role-assignments",
            json=_role_assignment_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["target_id"] == _role_assignment_create.target_id
        assert payload["role_id"] == _role_assignment_create.role_id
        assert payload["resource_id"] == _role_assignment_create.resource_id


def test_api_create_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_role_platform_creator: "Role",
):
    target_role = deps_role_platform_creator

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        _role_assignment_create = RoleAssignmentCreate(
            target_id=deps_user_newbie[0].id,
            role_id=target_role.id,
            resource_id=deps_project.id,
        )
        response = test_api_client.post(
            "/v1/role-assignments",
            json=_role_assignment_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_retrieve_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_role_assignment_platform_creator: "RoleAssignment",
):
    role_assignment = deps_role_assignment_platform_creator

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            f"/v1/role-assignments/{role_assignment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["id"] == role_assignment.id


def test_api_retrieve_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_role_assignment_platform_creator: "RoleAssignment",
):
    role_assignment = deps_role_assignment_platform_creator

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            f"/v1/role-assignments/{role_assignment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_role_platform_creator: "Role",
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        _role_assignment_create = RoleAssignmentCreate(
            target_id=deps_user_newbie[0].id,
            role_id=deps_role_platform_creator.id,
            resource_id=deps_project.id,
        )
        _role_assignment_created = backend_client.role_assignments.create(
            _role_assignment_create
        )

        response = test_api_client.delete(
            f"/v1/role-assignments/{_role_assignment_created.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_role_assignment_platform_creator: "RoleAssignment",
):
    role_assignment = deps_role_assignment_platform_creator

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.delete(
            f"/v1/role-assignments/{role_assignment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
