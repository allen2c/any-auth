import time
import typing

import fastapi
import pytest
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.api_key import APIKey, APIKeyCreate
from any_auth.types.project import Project
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import RoleAssignmentCreate
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

    assert response.status_code == fastapi.status.HTTP_200_OK
    assert response.json()["success"] is True


# @pytest.mark.asyncio
# async def test_verify_with_blacklisted_token(
#     test_api_client: TestClient,
#     deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
#     deps_project: Project,
#     deps_backend_client_session_with_all_resources: BackendClient,
#     deps_app_cache: typing.Any,
# ):
#     user, token = deps_user_platform_manager
#     project_id = deps_project.id

#     # Blacklist the token
#     deps_app_cache.set(f"token_blacklist:{token}", True)

#     # Attempt verification with blacklisted token
#     response = test_api_client.post(
#         "/verify",
#         json={"resource_id": project_id, "permissions": "project:view"},
#         headers={"Authorization": f"Bearer {token}"},
#     )

#     assert response.status_code == HTTP_401_UNAUTHORIZED
#     assert "Token blacklisted" in response.json()["detail"]


# @pytest.mark.asyncio
# async def test_verify_with_invalid_token(


# @pytest.mark.asyncio
# async def test_verify_with_expired_token(


# @pytest.mark.asyncio
# async def test_verify_with_insufficient_permissions(


# @pytest.mark.asyncio
# async def test_verify_with_non_existent_resource(
