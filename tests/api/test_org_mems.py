import typing

from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import (
    Organization,
)
from any_auth.types.organization_member import OrganizationMemberCreate
from any_auth.types.user import UserInDB


def test_api_list_organization_members(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
    ]:
        response = test_api_client.get(
            f"/v1/organizations/{organization_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"User {user.username} failed to list organization members: {response.text}"

        payload = response.json()

        assert payload["object"] == "list"
        assert len(payload["data"]) >= 0
        assert payload["has_more"] is False


def test_api_list_organization_members_denied(
    test_api_client: TestClient,
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            f"/v1/organizations/{organization_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 403
        ), f"User {user.username} failed to list organization members: {response.text}"


def test_api_create_organization_member(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
    ]:
        # Create a member
        _member_create = OrganizationMemberCreate(
            user_id=deps_user_newbie[0].id,
        )
        response = test_api_client.post(
            f"/v1/organizations/{organization_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"User {user.username} failed to create organization member: {response.text}"
        payload = response.json()
        assert payload["user_id"] == _member_create.user_id


def test_api_create_organization_member_denied(
    test_api_client: TestClient,
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        _member_create = OrganizationMemberCreate(
            user_id=deps_user_newbie[0].id,
        )
        response = test_api_client.post(
            f"/v1/organizations/{organization_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 403
        ), f"User {user.username} failed to create organization member: {response.text}"


def test_api_retrieve_organization_member(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_org: Organization,
):
    organization_id = deps_org.id
    backend_client_session = deps_backend_client_session_with_all_resources

    organization_members = backend_client_session.organization_members.list(
        organization_id=organization_id
    ).data
    assert len(organization_members) > 0

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
    ]:
        # Retrieve the member
        response = test_api_client.get(
            f"/v1/organizations/{organization_id}/members/{organization_members[0].id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"User {user.username} failed to retrieve organization member: {response.text}"  # noqa: E501

        retrieved_member_payload = response.json()
        assert retrieved_member_payload["id"] == organization_members[0].id


def test_api_retrieve_organization_member_denied(
    test_api_client: TestClient,
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            f"/v1/organizations/{organization_id}/members/any_member_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 403
        ), f"User {user.username} failed to retrieve organization member: {response.text}"  # noqa: E501


def test_api_delete_organization_member(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_org_owner,
    ]:
        # Create a member for newbie
        response = test_api_client.post(
            f"/v1/organizations/{organization_id}/members",
            json=OrganizationMemberCreate(user_id=deps_user_newbie[0].id).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"User {user.username} failed to create organization member: {response.text}"
        created_member_payload = response.json()

        # Delete the member
        response = test_api_client.delete(
            (
                f"/v1/organizations/{organization_id}"
                + f"/members/{created_member_payload['id']}"
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 204
        ), f"User {user.username} failed to delete organization member: {response.text}"  # noqa: E501


def test_api_delete_organization_member_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    organization_id = deps_org.id

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        # Delete the member
        response = test_api_client.delete(
            f"/v1/organizations/{organization_id}/members/any_member_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 403
        ), f"User {user.username} failed to delete organization member: {response.text}"  # noqa: E501
