import typing

import pytest
from fastapi.testclient import TestClient

from any_auth.types.organization import Organization
from any_auth.types.pagination import Page
from any_auth.types.project import Project
from any_auth.types.user import UserInDB


@pytest.mark.asyncio
async def test_api_root_me(
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
async def test_api_root_me_organizations(
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
async def test_api_root_me_projects(
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
