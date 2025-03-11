import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import (
    Organization,
)
from any_auth.types.organization_member import OrganizationMemberCreate
from any_auth.types.user import UserInDB


def test_api_list_organization_members(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
    ]:
        response = test_client_module.get(
            f"/organizations/{organization_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) >= 0
        assert payload["has_more"] is False


def test_api_list_organization_members_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
):
    organization_id = org_of_session.id

    for user, token in [
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.get(
            f"/organizations/{organization_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_create_organization_member(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [user_platform_manager, user_platform_creator, user_org_owner]:
        # Create a member
        _member_create = OrganizationMemberCreate(
            user_id=user_newbie[0].id,
        )
        response = test_client_module.post(
            f"/organizations/{organization_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == _member_create.user_id


def test_api_create_organization_member_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        _member_create = OrganizationMemberCreate(
            user_id=user_newbie[0].id,
        )
        response = test_client_module.post(
            f"/organizations/{organization_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_retrieve_organization_member(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    backend_client_session: "BackendClient",
    org_of_session: Organization,
):
    organization_id = org_of_session.id
    organization_members = backend_client_session.organization_members.list(
        organization_id=organization_id
    ).data
    assert len(organization_members) > 0

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
    ]:
        # Retrieve the member
        response = test_client_module.get(
            f"/organizations/{organization_id}/members/{organization_members[0].id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        retrieved_member_payload = response.json()
        assert retrieved_member_payload["id"] == organization_members[0].id


def test_api_retrieve_organization_member_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
):
    organization_id = org_of_session.id

    for user, token in [
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.get(
            f"/organizations/{organization_id}/members/any_member_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_delete_organization_member(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_org_owner,
    ]:
        # Create a member for newbie
        response = test_client_module.post(
            f"/organizations/{organization_id}/members",
            json=OrganizationMemberCreate(user_id=user_newbie[0].id).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        created_member_payload = response.json()

        # Delete the member
        response = test_client_module.delete(
            f"/organizations/{organization_id}/members/{created_member_payload['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204


def test_api_delete_organization_member_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_creator,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        # Delete the member
        response = test_client_module.delete(
            f"/organizations/{organization_id}/members/any_member_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
