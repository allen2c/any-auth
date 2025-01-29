import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from any_auth.types.organization_member import OrganizationMemberCreate
from any_auth.types.user import UserInDB


def test_api_list_organizations(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test listing organizations when there are no organizations in the database.
    """

    for user, token in [user_platform_manager, user_platform_creator]:
        response = test_client_module.get(
            "/organizations", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) >= 0
        assert payload["has_more"] is False


def test_api_list_organizations_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.get(
            "/organizations", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_create_organization(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [user_platform_creator, user_platform_manager]:
        _organization_create = OrganizationCreate.fake(fake)

        response = test_client_module.post(
            "/organizations",
            json=_organization_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == _organization_create.name
        assert payload["full_name"] == _organization_create.full_name
        assert payload["metadata"] == _organization_create.metadata


def test_api_create_organization_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.post(
            "/organizations",
            json=OrganizationCreate.fake(fake).model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_retrieve_organization(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
):
    """Test retrieving organization info."""

    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
    ]:
        response = test_client_module.get(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        retrieved_payload = response.json()
        assert retrieved_payload["id"] == org_of_session.id
        assert retrieved_payload["name"] == org_of_session.name
        assert retrieved_payload["full_name"] == org_of_session.full_name
        assert retrieved_payload["metadata"] == org_of_session.metadata


def test_api_retrieve_organization_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_org_owner
    response = test_client_module.get(
        "/organizations/invalid_organization_id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_retrieve_organization_denied(
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
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_update_organization(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_org_owner,
        user_org_editor,
    ]:
        _organization_update = OrganizationUpdate(full_name=fake.company())
        response = test_client_module.post(
            f"/organizations/{organization_id}",
            json=_organization_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        updated_payload = response.json()
        assert updated_payload["id"] == org_of_session.id
        assert updated_payload["full_name"] == _organization_update.full_name


def test_api_update_organization_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    user, token = user_org_owner
    response = test_client_module.post(
        "/organizations/invalid_organization_id",
        json=OrganizationUpdate(full_name=fake.company()).model_dump(exclude_none=True),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_update_organization_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_creator,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        _organization_update = OrganizationUpdate(full_name=fake.company())
        response = test_client_module.post(
            f"/organizations/{organization_id}",
            json=_organization_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_delete_organization(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [user_platform_manager, user_org_owner]:
        response = test_client_module.delete(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Ensure that the organization is disabled
        response = test_client_module.get(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True


def test_api_delete_organization_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_org_owner
    response = test_client_module.delete(
        "/organizations/invalid_organization_id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_delete_organization_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
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
        response = test_client_module.delete(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_enable_organization(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [user_org_owner]:
        response = test_client_module.delete(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Ensure that the organization is disabled
        response = test_client_module.get(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True

        # Enable the organization
        response = test_client_module.post(
            f"/organizations/{organization_id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Ensure that the organization is now enabled
        response = test_client_module.get(
            f"/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is False


def test_api_enable_organization_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_org_owner
    response = test_client_module.post(
        "/organizations/invalid_organization_id/enable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_enable_organization_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
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
        response = test_client_module.post(
            f"/organizations/{organization_id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


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
    user_newbie: UserInDB,
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [user_platform_manager, user_platform_creator, user_org_owner]:
        # Create a member
        _member_create = OrganizationMemberCreate(
            user_id=user_newbie.id,
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
    user_newbie: UserInDB,
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
            user_id=user_newbie.id,
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
    org_of_session: Organization,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_org_owner,
    ]:
        # Create a member
        response = test_client_module.post(
            f"/organizations/{organization_id}/members",
            json=OrganizationMemberCreate(user_id=user.id).model_dump(
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
