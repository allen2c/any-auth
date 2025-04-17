import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.oauth_client import OAuthClient, OAuthClientCreate
from any_auth.types.project import Project
from any_auth.types.user import UserInDB


# === Test POST /oauth/clients ===
def test_api_create_oauth_client_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_fake: Faker,
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users with IAM_SET_POLICY can create OAuth clients."""
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        create_data = OAuthClientCreate.model_validate(
            {
                "name": deps_fake.company() + "_client",
                "redirect_uris": [deps_fake.url()],
                "scopes": ["openid", "email"],
                "project_id": project_id,
            }
        )
        response = test_api_client.post(
            "/v1/oauth/clients",
            json=create_data.model_dump(exclude_none=True, mode="json"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = OAuthClient(**response.json())
        assert payload.name == create_data.name
        assert payload.project_id == project_id


def test_api_create_oauth_client_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_fake: Faker,
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users without IAM_SET_POLICY cannot create OAuth clients."""
    project_id = deps_project.id
    create_data = OAuthClientCreate.model_validate(
        {
            "name": deps_fake.company() + "_denied_client",
            "redirect_uris": [deps_fake.url()],
            "scopes": ["openid"],
            "project_id": project_id,
        }
    )

    denied_users = [
        # PlatformCreator has IAM_SET_POLICY so is not denied
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]

    for user, token in denied_users:
        response = test_api_client.post(
            "/v1/oauth/clients",
            json=create_data.model_dump(exclude_none=True, mode="json"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


# === Test GET /oauth/clients ===
def test_api_list_oauth_clients_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users with IAM_GET_POLICY can list OAuth clients for a project."""

    project_id = deps_project.id

    allowed_users = [
        deps_user_platform_manager,  # Has IAM_GET_POLICY
        deps_user_platform_creator,  # Has IAM_GET_POLICY
    ]

    for user, token in allowed_users:
        response = test_api_client.get(
            f"/v1/oauth/clients?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["object"] == "list"
        assert isinstance(payload["data"], list)


def test_api_list_oauth_clients_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users without IAM_GET_POLICY cannot list OAuth clients."""
    project_id = deps_project.id
    denied_users = [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]

    for user, token in denied_users:
        response = test_api_client.get(
            f"/v1/oauth/clients?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


# === Test GET /oauth/clients/{client_id} ===


def test_api_retrieve_oauth_client_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users with IAM_GET_POLICY can retrieve a specific OAuth client."""

    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id

    created_oauth_client = backend_client.oauth_clients.create(
        OAuthClientCreate.model_validate(
            {
                "name": deps_fake.company() + "_client",
                "redirect_uris": [deps_fake.url()],
                "scopes": ["openid", "email"],
                "project_id": project_id,
            }
        )
    )
    assert created_oauth_client is not None

    allowed_users = [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]

    for user, token in allowed_users:
        response = test_api_client.get(
            f"/v1/oauth/clients/{created_oauth_client.client_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = OAuthClient(**response.json())
        assert payload.client_id == created_oauth_client.client_id


def test_api_retrieve_oauth_client_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users without IAM_GET_POLICY cannot retrieve a specific OAuth client."""  # noqa: E501

    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources

    created_oauth_client = backend_client.oauth_clients.create(
        OAuthClientCreate.model_validate(
            {
                "name": deps_fake.company() + "_client",
                "redirect_uris": [deps_fake.url()],
                "scopes": ["openid", "email"],
                "project_id": project_id,
            }
        )
    )

    denied_users = [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]

    for user, token in denied_users:
        response = test_api_client.get(
            f"/v1/oauth/clients/{created_oauth_client.client_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


# === Test PATCH /oauth/clients/{client_id}/disable ===
# === Test PATCH /oauth/clients/{client_id}/enable ===
def test_api_disable_enable_oauth_client_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, str],
    deps_user_platform_creator: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users with IAM_SET_POLICY can disable and enable an OAuth client."""

    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources

    created_oauth_client = backend_client.oauth_clients.create(
        OAuthClientCreate.model_validate(
            {
                "name": deps_fake.company() + "_client",
                "redirect_uris": [deps_fake.url()],
                "scopes": ["openid", "email"],
                "project_id": project_id,
            }
        )
    )
    assert created_oauth_client is not None

    allowed_users = [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]

    for user, token in allowed_users:
        # Ensure it's enabled first (might have been disabled by previous iteration)
        test_api_client.patch(
            f"/v1/oauth/clients/{created_oauth_client.client_id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Disable it
        response = test_api_client.patch(
            f"/v1/oauth/clients/{created_oauth_client.client_id}/disable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed to disable, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = OAuthClient(**response.json())
        assert payload.disabled is True

        # Enable it
        response = test_api_client.patch(
            f"/v1/oauth/clients/{created_oauth_client.client_id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed to enable, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = OAuthClient(**response.json())
        assert payload.disabled is False


def test_api_disable_enable_oauth_client_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, str],
    deps_user_org_editor: typing.Tuple[UserInDB, str],
    deps_user_org_viewer: typing.Tuple[UserInDB, str],
    deps_user_project_owner: typing.Tuple[UserInDB, str],
    deps_user_project_editor: typing.Tuple[UserInDB, str],
    deps_user_project_viewer: typing.Tuple[UserInDB, str],
    deps_user_newbie: typing.Tuple[UserInDB, str],
    deps_project: Project,
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,  # Required
):
    """Tests that users without IAM_SET_POLICY cannot disable an OAuth client."""

    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources

    created_oauth_client = backend_client.oauth_clients.create(
        OAuthClientCreate.model_validate(
            {
                "name": deps_fake.company() + "_client",
                "redirect_uris": [deps_fake.url()],
                "scopes": ["openid", "email"],
                "project_id": project_id,
            }
        )
    )
    denied_users = [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]

    for user, token in denied_users:
        response = test_api_client.patch(
            f"/v1/oauth/clients/{created_oauth_client.client_id}/disable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied from disabling, "
            + f"but got {response.status_code}: {response.text}"
        )

        response = test_api_client.patch(
            f"/v1/oauth/clients/{created_oauth_client.client_id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied from enabling, "
            + f"but got {response.status_code}: {response.text}"
        )
