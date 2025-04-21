import typing

import fastapi
import pytest
from fastapi.testclient import TestClient

from any_auth.types.api.me import (
    MePermissionsEvaluateRequest,
    MePermissionsEvaluateResponse,
    MePermissionsResponse,
)
from any_auth.types.organization import Organization
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.role import Role
from any_auth.types.user import UserInDB


@pytest.mark.asyncio
async def test_api_me(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    user, token = deps_user_platform_creator
    response = test_api_client.get(
        "/v1/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    assert user.id == response.json()["id"]

    response = test_api_client.get("/v1/me")
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_api_me_organizations(
    test_api_client: TestClient,
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
):
    _, token = deps_user_org_editor
    response = test_api_client.get(
        "/v1/me/organizations", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    organizations = Page[Organization].model_validate(response.json())
    assert len(organizations.data) > 0

    response = test_api_client.get("/v1/me/organizations")
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_api_me_projects(
    test_api_client: TestClient,
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
):
    _, token = deps_user_project_viewer
    response = test_api_client.get(
        "/v1/me/projects", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    projects = Page[Project].model_validate(response.json())
    assert len(projects.data) > 0

    response = test_api_client.get("/v1/me/projects")
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_api_me_permissions(
    test_api_client: TestClient,
    deps_project: Project,
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_role_project_viewer: Role,
):
    user, token = deps_user_project_viewer

    response = test_api_client.get(
        "/v1/me/permissions",
        params={"projectId": deps_project.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert (
        response.status_code == fastapi.status.HTTP_200_OK
    ), f"{response.status_code}: {response.text}"
    data = MePermissionsResponse.model_validate(response.json())
    assert data.resource_id == deps_project.id
    assert data.user_id == user.id
    assert data.api_key_id is None
    assert len(data.roles) > 0
    assert len(data.permissions) > 0
    assert deps_role_project_viewer.name in data.roles
    assert set(data.permissions) == set(deps_role_project_viewer.permissions)


@pytest.mark.asyncio
async def test_api_me_permissions_evaluate_allowed(
    test_api_client: TestClient,
    deps_project: Project,
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_role_project_viewer: Role,
):
    _, token = deps_user_project_viewer
    # Use a permission that project viewer should have
    permission = deps_role_project_viewer.permissions[0]

    request = MePermissionsEvaluateRequest(
        resource_id=deps_project.id, permissions_to_check=[permission]
    )
    response = test_api_client.post(
        "/v1/me/permissions/evaluate",
        headers={"Authorization": f"Bearer {token}"},
        json=request.model_dump(exclude_none=True),
    )

    assert response.status_code == fastapi.status.HTTP_200_OK, response.text
    data = MePermissionsEvaluateResponse.model_validate(response.json())
    assert data.allowed is True


@pytest.mark.asyncio
async def test_api_me_permissions_evaluate_missing(
    test_api_client: TestClient,
    deps_project: Project,
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_role_project_viewer: Role,
):
    _, token = deps_user_project_viewer
    # Use a non-existent permission
    permission = "non.existent.permission"

    request = MePermissionsEvaluateRequest(
        resource_id=deps_project.id, permissions_to_check=[permission]
    )
    response = test_api_client.post(
        "/v1/me/permissions/evaluate",
        headers={"Authorization": f"Bearer {token}"},
        json=request.model_dump(exclude_none=True),
    )

    assert response.status_code == fastapi.status.HTTP_200_OK, response.text
    data = MePermissionsEvaluateResponse.model_validate(response.json())
    assert data.allowed is False
