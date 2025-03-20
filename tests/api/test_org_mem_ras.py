import typing

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
    test_api_client: TestClient,
    deps_user_platform_manager: tuple[UserInDB, str],
    deps_user_platform_creator: tuple[UserInDB, str],
    deps_user_org_owner: tuple[UserInDB, str],
    deps_user_org_editor: tuple[UserInDB, str],
    deps_user_org_viewer: tuple[UserInDB, str],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_org: Organization,
):
    org_id = deps_org.id
    backend_client_session = deps_backend_client_session_with_all_resources

    # Ensure there's at least one member in this organization
    org_members = backend_client_session.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    member_id = org_members[0].id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = test_api_client.get(
            f"/organizations/{org_id}/members/{member_id}/rs",
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"User {user.model_dump_json()} with IAM_GET_POLICY at the organization "
            f"should succeed. Got status={resp.status_code}."
        )
        data = resp.json()
        assert data["object"] == "list"


def test_api_retrieve_organization_member_role_assignments_denied(
    test_api_client: TestClient,
    deps_user_project_owner: tuple[UserInDB, str],
    deps_user_project_editor: tuple[UserInDB, str],
    deps_user_project_viewer: tuple[UserInDB, str],
    deps_user_newbie: tuple[UserInDB, str],
    deps_org: Organization,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    org_id = deps_org.id
    member_id = _get_at_least_one_org_member_id(
        backend_client_session=deps_backend_client_session_with_all_resources,
        org_id=org_id,
    )

    for user, token in [
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = test_api_client.get(
            f"/organizations/{org_id}/members/{member_id}/rs",
            headers=headers,
        )
        # Fails with 403 due to lacking IAM_GET_POLICY on org scope
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_GET_POLICY at org "
            f"should fail. Got response={resp.text}."
        )


def test_api_create_organization_member_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: tuple[UserInDB, str],
    deps_user_platform_creator: tuple[UserInDB, str],
    deps_user_org_owner: tuple[UserInDB, str],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_org: Organization,
    deps_user_newbie: tuple[UserInDB, str],
    deps_role_na: Role,  # Example: some role to assign
):
    org_id = deps_org.id
    backend_client_session = deps_backend_client_session_with_all_resources

    # Grab or create a known existing member in the org
    org_members = backend_client_session.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    org_member = org_members[0]
    member_id = org_member.id

    # We'll attempt to assign some test role (for example, `role_na`).
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
    ]:
        url = f"/organizations/{org_id}/members/{member_id}/rs"
        req_body = MemberRoleAssignmentCreate(role=deps_role_na.name).model_dump(
            exclude_none=True
        )
        resp = test_api_client.post(
            url, json=req_body, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, (
            f"User {user.model_dump_json()} with IAM_SET_POLICY at org "
            f"should succeed in creating assignment. "
            f"Got {resp.status_code}: {resp.text}."
        )
        data = resp.json()
        assert data["resource_id"] == org_id
        # target_id must match the org_member's user_id
        assert data["target_id"] == org_member.user_id


def test_api_create_organization_member_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_editor: tuple[UserInDB, str],
    deps_user_org_viewer: tuple[UserInDB, str],
    deps_user_project_owner: tuple[UserInDB, str],
    deps_user_project_editor: tuple[UserInDB, str],
    deps_user_project_viewer: tuple[UserInDB, str],
    deps_user_newbie: tuple[UserInDB, str],
    deps_org: Organization,
    deps_role_na: Role,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    org_id = deps_org.id
    member_id = _get_at_least_one_org_member_id(
        backend_client_session=deps_backend_client_session_with_all_resources,
        org_id=org_id,
    )

    url = f"/organizations/{org_id}/members/{member_id}/rs"
    body = MemberRoleAssignmentCreate(role=deps_role_na.name).model_dump(
        exclude_none=True
    )

    for user, token in [
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        resp = test_api_client.post(
            url, json=body, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_SET_POLICY at org "
            f"should fail. Got {resp.status_code}: {resp.text}."
        )


def test_api_delete_organization_member_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: tuple[UserInDB, str],
    deps_user_platform_creator: tuple[UserInDB, str],
    deps_user_org_owner: tuple[UserInDB, str],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_org: Organization,
    deps_role_na: Role,
):
    org_id = deps_org.id
    backend_client_session = deps_backend_client_session_with_all_resources

    # We need an actual role assignment to delete, so let's get or create an org member:
    org_members = backend_client_session.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    org_member = org_members[0]
    member_id = org_member.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
    ]:
        # Create a role assignment to then delete:
        assignment = backend_client_session.role_assignments.create(
            RoleAssignmentCreate(
                target_id=org_member.user_id,
                role_id=deps_role_na.id,
                resource_id=org_id,
            )
        )

        # Delete the role assignment:
        url = f"/organizations/{org_id}/members/{member_id}/rs/{assignment.id}"
        resp = test_api_client.delete(url, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204, (
            f"User {user.model_dump_json()} with IAM_SET_POLICY at org can delete. "
            f"Got status={resp.status_code}."
        )


def test_api_delete_organization_member_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_org_editor: tuple[UserInDB, str],
    deps_user_org_viewer: tuple[UserInDB, str],
    deps_user_project_owner: tuple[UserInDB, str],
    deps_user_project_editor: tuple[UserInDB, str],
    deps_user_project_viewer: tuple[UserInDB, str],
    deps_user_newbie: tuple[UserInDB, str],
    deps_org: Organization,
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_role_na: Role,
):
    org_id = deps_org.id
    backend_client_session = deps_backend_client_session_with_all_resources

    # Create a dummy assignment to attempt deleting:
    # For the sake of the test, we can reuse an existing org member if any:
    org_members = backend_client_session.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"

    org_member = org_members[0]
    member_id = org_member.id

    # Ensure there's at least one existing assignment to the org:
    assignment = backend_client_session.role_assignments.create(
        RoleAssignmentCreate(
            target_id=org_member.user_id,
            role_id=deps_role_na.id,
            resource_id=org_id,
        )
    )

    for user, token in [
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        url = f"/organizations/{org_id}/members/{member_id}/rs/{assignment.id}"
        resp = test_api_client.delete(url, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, (
            f"User {user.model_dump_json()} lacking IAM_SET_POLICY at org "
            f"should not be able to delete. Got status={resp.status_code}."
        )


def _get_at_least_one_org_member_id(
    backend_client_session: BackendClient,
    org_id: typing.Text,
) -> typing.Text:
    # Ensure there's at least one member in this organization
    org_members = backend_client_session.organization_members.list(
        organization_id=org_id
    ).data
    assert len(org_members) > 0, "We need at least 1 organization_member"
    return org_members[0].id
