from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import (
    Organization,
)
from any_auth.types.role import Role
from any_auth.types.role_assignment import (
    MemberRoleAssignmentCreate,
    RoleAssignmentCreate,
)
from any_auth.types.user import UserInDB


def test_api_retrieve_organization_member_role_assignments_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: tuple[UserInDB, str],
    user_platform_creator: tuple[UserInDB, str],
    user_org_owner: tuple[UserInDB, str],
    user_org_editor: tuple[UserInDB, str],
    user_org_viewer: tuple[UserInDB, str],
    backend_client_session_with_roles: BackendClient,
    org_of_session: Organization,
):
    org_id = org_of_session.id

    # Ensure there's at least one member in this organization
    org_members = backend_client_session_with_roles.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    member_id = org_members[0].id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = test_client_module.get(
            f"/organizations/{org_id}/members/{member_id}/role-assignments",
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"User {user.model_dump_json()} with IAM_GET_POLICY at the organization "
            f"should succeed. Got status={resp.status_code}."
        )
        data = resp.json()
        assert data["object"] == "list"


def test_api_retrieve_organization_member_role_assignments_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_project_owner: tuple[UserInDB, str],
    user_project_editor: tuple[UserInDB, str],
    user_project_viewer: tuple[UserInDB, str],
    user_newbie: tuple[UserInDB, str],
    org_of_session: Organization,
):
    org_id = org_of_session.id

    for user, token in [
        user_project_owner,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = test_client_module.get(
            f"/organizations/{org_id}/members/any_member_id/role-assignments",
            headers=headers,
        )
        # Fails with 403 due to lacking IAM_GET_POLICY on org scope
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_GET_POLICY at org "
            f"should fail. Got status={resp.status_code}."
        )


def test_api_create_organization_member_role_assignment_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: tuple[UserInDB, str],
    user_platform_creator: tuple[UserInDB, str],
    user_org_owner: tuple[UserInDB, str],
    backend_client_session_with_roles: BackendClient,
    org_of_session: Organization,
    user_newbie: tuple[UserInDB, str],
    role_na: Role,  # Example: some role to assign
):
    org_id = org_of_session.id
    # Grab or create a known existing member in the org
    org_members = backend_client_session_with_roles.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    org_member = org_members[0]
    member_id = org_member.id

    # We'll attempt to assign some test role (for example, `role_na`).
    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
    ]:
        url = f"/organizations/{org_id}/members/{member_id}/role-assignments"
        req_body = MemberRoleAssignmentCreate(role=role_na.name).model_dump(
            exclude_none=True
        )
        resp = test_client_module.post(
            url, json=req_body, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, (
            f"User {user.model_dump_json()} with IAM_SET_POLICY at org "
            f"should succeed in creating assignment. "
            f"Got {resp.status_code}: {resp.text}."
        )
        data = resp.json()
        assert data["resource_id"] == org_id
        # user_id must match the org_member's user_id
        assert data["user_id"] == org_member.user_id


def test_api_create_organization_member_role_assignment_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_editor: tuple[UserInDB, str],
    user_org_viewer: tuple[UserInDB, str],
    user_project_owner: tuple[UserInDB, str],
    user_project_editor: tuple[UserInDB, str],
    user_project_viewer: tuple[UserInDB, str],
    user_newbie: tuple[UserInDB, str],
    org_of_session: Organization,
    role_na: Role,
):
    org_id = org_of_session.id
    url = f"/organizations/{org_id}/members/any_member_id/role-assignments"
    body = MemberRoleAssignmentCreate(role=role_na.name).model_dump(exclude_none=True)

    for user, token in [
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        resp = test_client_module.post(
            url, json=body, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_SET_POLICY at org "
            f"should fail. Got {resp.status_code}: {resp.text}."
        )


def test_api_delete_organization_member_role_assignment_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: tuple[UserInDB, str],
    user_platform_creator: tuple[UserInDB, str],
    user_org_owner: tuple[UserInDB, str],
    backend_client_session_with_roles: BackendClient,
    org_of_session: Organization,
    user_newbie: tuple[UserInDB, str],
    role_na: Role,
):
    org_id = org_of_session.id

    # We need an actual role assignment to delete, so let's get or create an org member:
    org_members = backend_client_session_with_roles.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    org_member = org_members[0]
    member_id = org_member.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
    ]:
        # Create a role assignment to then delete:
        assignment = backend_client_session_with_roles.role_assignments.create(
            RoleAssignmentCreate(
                user_id=org_member.user_id,
                role_id=role_na.id,
                resource_id=org_id,
            )
        )

        # Delete the role assignment:
        url = (
            f"/organizations/{org_id}/members/{member_id}"
            f"/role-assignments/{assignment.id}"
        )
        resp = test_client_module.delete(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 204, (
            f"User {user.model_dump_json()} with IAM_SET_POLICY at org can delete. "
            f"Got status={resp.status_code}."
        )


def test_api_delete_organization_member_role_assignment_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_editor: tuple[UserInDB, str],
    user_org_viewer: tuple[UserInDB, str],
    user_project_owner: tuple[UserInDB, str],
    user_project_editor: tuple[UserInDB, str],
    user_project_viewer: tuple[UserInDB, str],
    user_newbie: tuple[UserInDB, str],
    org_of_session: Organization,
    backend_client_session_with_roles: BackendClient,
    role_na: Role,
):
    org_id = org_of_session.id

    # Create a dummy assignment to attempt deleting:
    # For the sake of the test, we can reuse an existing org member if any:
    org_members = backend_client_session_with_roles.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"

    org_member = org_members[0]
    member_id = org_member.id

    # Ensure there's at least one existing assignment to the org:
    assignment = backend_client_session_with_roles.role_assignments.create(
        RoleAssignmentCreate(
            user_id=org_member.user_id,
            role_id=role_na.id,
            resource_id=org_id,
        )
    )

    for user, token in [
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        url = (
            f"/organizations/{org_id}/members/{member_id}"
            f"/role-assignments/{assignment.id}"
        )
        resp = test_client_module.delete(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_SET_POLICY at org "
            f"should not be able to delete. Got status={resp.status_code}."
        )
