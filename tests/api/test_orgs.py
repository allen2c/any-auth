import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from any_auth.types.user import UserInDB


# === Endpoint: /organizations ===
def test_api_list_organizations(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test listing organizations when there are no organizations in the database.
    """

    for _, token in [deps_user_platform_manager, deps_user_platform_creator]:
        response = test_api_client.get(
            "/organizations", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) >= 0
        assert payload["has_more"] is False


def test_api_list_organizations_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
):
    for _, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            "/organizations", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


# === Endpoint: /organizations/{organization_id} ===
def test_api_create_organization(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for _user, token in [deps_user_platform_creator, deps_user_platform_manager]:
        _organization_create = OrganizationCreate.fake(fake=deps_fake)

        response = test_api_client.post(
            "/organizations",
            json=_organization_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"User {_user.username} failed to create organization: {response.text}"
        payload = response.json()
        assert payload["name"] == _organization_create.name
        assert payload["full_name"] == _organization_create.full_name
        assert payload["metadata"] == _organization_create.metadata


def test_api_create_organization_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for _, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.post(
            "/organizations",
            json=OrganizationCreate.fake(fake=deps_fake).model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_retrieve_organization(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    """Test retrieving organization info."""

    for _user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
    ]:
        response = test_api_client.get(
            f"/organizations/{deps_org.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"User {_user.username} failed to retrieve organization: {response.text}"
        retrieved_payload = response.json()
        assert retrieved_payload["id"] == deps_org.id
        assert retrieved_payload["name"] == deps_org.name
        assert retrieved_payload["full_name"] == deps_org.full_name
        assert retrieved_payload["metadata"] == deps_org.metadata


def test_api_retrieve_organization_not_found(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    for _, token in [deps_user_org_owner]:
        response = test_api_client.get(
            "/organizations/invalid_organization_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, f"Response: {response.text}"


def test_api_retrieve_organization_denied(
    test_api_client: TestClient,
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    for _, token in [
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            f"/organizations/{deps_org.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_update_organization(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_fake: Faker,
):
    for _, token in [
        deps_user_platform_manager,
        deps_user_org_owner,
        deps_user_org_editor,
    ]:
        _organization_update = OrganizationUpdate(full_name=deps_fake.company())
        response = test_api_client.put(
            f"/organizations/{deps_org.id}",
            json=_organization_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        updated_payload = response.json()
        assert updated_payload["id"] == deps_org.id
        assert updated_payload["full_name"] == _organization_update.full_name


def test_api_update_organization_not_found(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for _, token in [deps_user_org_owner]:
        response = test_api_client.put(
            "/organizations/invalid_organization_id",
            json=OrganizationUpdate(full_name=deps_fake.company()).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, f"Response: {response.text}"


def test_api_update_organization_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_fake: Faker,
):
    for _, token in [
        deps_user_platform_creator,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        _organization_update = OrganizationUpdate(full_name=deps_fake.company())
        response = test_api_client.put(
            f"/organizations/{deps_org.id}",
            json=_organization_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_delete_organization(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_backend_client_session_with_all_resources: "BackendClient",
):
    backend_client_session = deps_backend_client_session_with_all_resources

    for _user, token in [deps_user_org_owner, deps_user_platform_manager]:
        response = test_api_client.delete(
            f"/organizations/{deps_org.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 204
        ), f"User {_user.username} failed to delete organization: {response.text}"

        # Ensure that the organization is disabled
        response = test_api_client.get(
            f"/organizations/{deps_org.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 403
        ), f"User {_user.username} failed to retrieve organization: {response.text}"

        # Ensure that the organization is enabled
        backend_client_session.organizations.set_disabled(deps_org.id, disabled=False)


def test_api_delete_organization_not_found(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    for _, token in [deps_user_org_owner]:
        response = test_api_client.delete(
            "/organizations/invalid_organization_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, f"Response: {response.text}"


def test_api_delete_organization_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
    deps_fake: Faker,
):
    for _, token in [
        deps_user_platform_creator,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.delete(
            f"/organizations/{deps_org.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_enable_organization(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    for _, token in [deps_user_org_owner, deps_user_platform_manager]:
        # Enable the organization
        response = test_api_client.post(
            f"/organizations/{deps_org.id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Ensure that the organization is now enabled
        response = test_api_client.get(
            f"/organizations/{deps_org.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is False


def test_api_enable_organization_not_found(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    for _, token in [deps_user_org_owner]:
        response = test_api_client.post(
            "/organizations/invalid_organization_id/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, f"Response: {response.text}"


def test_api_enable_organization_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_org: Organization,
):
    for _, token in [
        deps_user_platform_creator,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.post(
            f"/organizations/{deps_org.id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
