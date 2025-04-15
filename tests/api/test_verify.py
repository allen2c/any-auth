import time
import typing
from pprint import pformat

import fastapi
import pytest
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.api_key import APIKey, APIKeyCreate
from any_auth.types.project import Project
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import PLATFORM_ID, RoleAssignmentCreate
from any_auth.types.user import UserInDB


@pytest.mark.asyncio
async def test_verify_with_valid_jwt_token(
    test_api_client: TestClient,
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    _, token = deps_user_project_editor
    project_id = deps_project.id

    # Platform managers should now have access to these custom permissions
    response = test_api_client.post(
        "/verify",
        json={
            "resource_id": project_id,
            "permissions": f"{Permission.PROJECT_GET},{Permission.PROJECT_UPDATE}",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == fastapi.status.HTTP_200_OK
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_verify_with_valid_api_key(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_role_project_editor: Role,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    user, _ = deps_user_platform_manager
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources

    # Create an API key and assign it to the project
    plain_key = APIKey.generate_plain_api_key()
    created_api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name="Test API Key",
            description="Test API key for verify endpoint",
            expires_at=int(time.time()) + 3600,
        ),
        created_by=user.id,
        resource_id=project_id,
        plain_key=plain_key,
    )
    # Assign the role to the API key
    backend_client.role_assignments.create(
        RoleAssignmentCreate(
            role_id=deps_role_project_editor.id,
            target_id=created_api_key.id,
            resource_id=project_id,
        )
    )

    # Verify with API key
    response = test_api_client.post(
        "/verify",
        json={
            "resource_id": project_id,
            "permissions": f"{Permission.PROJECT_GET},{Permission.PROJECT_UPDATE}",
        },
        headers={"Authorization": f"Bearer {plain_key}"},
    )

    assert (
        response.status_code == fastapi.status.HTTP_200_OK
    ), f"Got {response.status_code}: {response.text}"
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_verify_with_invalid_token(
    test_api_client: TestClient,
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    token = "invalid_token_that_does_not_exist"
    project_id = deps_project.id

    # Attempt verification with invalid token
    response = test_api_client.post(
        "/verify",
        json={"resource_id": project_id, "permissions": Permission.PROJECT_GET},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert pformat(response.json()) == pformat({"detail": "Invalid token"})


@pytest.mark.asyncio
async def test_verify_with_expired_token(
    test_api_client: TestClient,
    deps_user_platform_creator_expired_token: typing.Tuple["UserInDB", typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    _, token = deps_user_platform_creator_expired_token

    response = test_api_client.post(
        "/verify",
        json={"resource_id": PLATFORM_ID, "permissions": Permission.USER_CREATE},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert pformat(response.json()) == pformat({"detail": "Token expired"})


@pytest.mark.asyncio
async def test_verify_with_insufficient_permissions(
    test_api_client: TestClient,
    deps_user_project_viewer: typing.Tuple["UserInDB", typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    user, token = deps_user_project_viewer
    project_id = deps_project.id

    response = test_api_client.post(
        "/verify",
        json={"resource_id": project_id, "permissions": Permission.USER_CREATE},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == fastapi.status.HTTP_403_FORBIDDEN
    assert pformat(response.json()) == pformat(
        {"detail": "Insufficient permissions"}
    ), f"Response: {response.json()}"


@pytest.mark.asyncio
async def test_verify_with_non_existent_resource(
    test_api_client: TestClient,
    deps_user_project_viewer: typing.Tuple["UserInDB", typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
):
    _, token = deps_user_project_viewer
    non_existent_resource_id = "non_existent_resource_id"

    response = test_api_client.post(
        "/verify",
        json={
            "resource_id": non_existent_resource_id,
            "permissions": Permission.PROJECT_GET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == fastapi.status.HTTP_403_FORBIDDEN
    assert pformat(response.json()) == pformat(
        {"detail": "Insufficient permissions"}
    ), f"Response: {response.json()}"
