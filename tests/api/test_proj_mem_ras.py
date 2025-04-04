import typing

from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember
from any_auth.types.role import Role
from any_auth.types.role_assignment import (
    MemberRoleAssignmentCreate,
    RoleAssignmentCreate,
)
from any_auth.types.user import UserInDB


def test_api_retrieve_project_member_role_assignments_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"/projects/{project_id}/members/{member_id}/role-assignments"
        resp = test_api_client.get(url, headers=headers)

        assert resp.status_code == 200, (
            f"User {user.model_dump_json()} with IAM_GET_POLICY for project "
            f"should succeed. Got status={resp.status_code}: {resp.text}."
        )
        data = resp.json()
        assert data["object"] == "list"


def test_api_retrieve_project_member_role_assignments_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        url = f"/projects/{project_id}/members/{member_id}/role-assignments"
        resp = test_api_client.get(url, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_GET_POLICY "
            + f"for project should fail. Got status={resp.status_code}: {resp.text}."
        )


def test_api_create_project_member_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_role_na: Role,
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
    ]:
        url = f"/projects/{project_id}/members/{member_id}/role-assignments"
        resp = test_api_client.post(
            url,
            json=MemberRoleAssignmentCreate(role=deps_role_na.name).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        # 200 on success
        assert resp.status_code == 200, (
            f"User {user.model_dump_json()} with IAM_SET_POLICY for project "
            + f"should succeed POST. Got status={resp.status_code}: {resp.text}."
        )
        data = resp.json()
        assert data["resource_id"] == project_id
        assert data["target_id"] == deps_project_member_of_project_viewer.user_id


def test_api_create_project_member_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_role_na: Role,
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
):
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        url = f"/projects/{project_id}/members/{member_id}/role-assignments"
        resp = test_api_client.post(
            url,
            json=MemberRoleAssignmentCreate(role=deps_role_na.name).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_SET_POLICY for project "
            + f"should fail. Got status={resp.status_code}: {resp.text}."
        )


def test_api_delete_project_member_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_role_na: Role,
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
    ]:
        # Create a role assignment
        role_assignments = backend_client.role_assignments.create(
            RoleAssignmentCreate(
                target_id=deps_project_member_of_project_viewer.user_id,
                role_id=deps_role_na.id,
                resource_id=project_id,
            ),
        )

        # Delete the role assignment
        url = (
            f"/projects/{project_id}/members/{member_id}"
            f"/role-assignments/{role_assignments.id}"
        )
        resp = test_api_client.delete(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204, (
            f"User {user.model_dump_json()} with IAM_SET_POLICY for project "
            + f"should succeed DELETE. Got status={resp.status_code}: {resp.text}."
        )


def test_api_delete_project_member_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_role_na: Role,
    deps_project: Project,
    deps_project_member_of_project_viewer: ProjectMember,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id
    member_id = deps_project_member_of_project_viewer.id

    role_assignments = backend_client.role_assignments.create(
        RoleAssignmentCreate(
            target_id=deps_project_member_of_project_viewer.user_id,
            role_id=deps_role_na.id,
            resource_id=project_id,
        ),
    )

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        url = (
            f"/projects/{project_id}/members/{member_id}"
            f"/role-assignments/{role_assignments.id}"
        )
        resp = test_api_client.delete(url, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_SET_POLICY for project "
            + f"should fail. Got status={resp.status_code}: {resp.text}."
        )
