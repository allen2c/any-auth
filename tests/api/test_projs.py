import typing

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.user import UserInDB


# --- Test Allowed Users ---
def test_api_list_projects_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            "/v1/projects",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["object"] == "list"


# --- Test Denied Users ---
def test_api_list_projects_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            "/v1/projects",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Create Project ---
def test_api_create_project_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        _project_create = ProjectCreate.fake(fake=deps_fake)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            "/v1/projects",
            json=_project_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["name"] == _project_create.name


# --- Test Create Project Denied ---
def test_api_create_project_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        _project_create = ProjectCreate.fake(fake=deps_fake)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            "/v1/projects",
            json=_project_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Retrieve Project ---
def test_api_retrieve_project_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/v1/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["id"] == project_id


# --- Test Retrieve Project Denied ---
def test_api_retrieve_project_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/v1/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


# --- Test Update Project ---
def test_api_update_project_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_fake: Faker,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_project_owner,
        deps_user_project_editor,
    ]:
        _project_update = ProjectUpdate(full_name=deps_fake.company())
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.put(
            f"/v1/projects/{project_id}",
            json=_project_update.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["id"] == project_id
        assert payload["full_name"] == _project_update.full_name


# --- Test Update Project Denied ---
def test_api_update_project_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_fake: Faker,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        _project_update = ProjectUpdate(full_name=deps_fake.company())
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.put(
            f"/v1/projects/{project_id}",
            json=_project_update.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Delete Project ---
def test_api_delete_project_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_manager,
        deps_user_project_owner,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.delete(
            f"/v1/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )

        # Recover the project
        backend_client.projects.set_disabled(project_id, disabled=False)


# --- Test Delete Project Denied ---
def test_api_delete_project_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.delete(
            f"/v1/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


def test_api_enable_project_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    # --- Test Allowed Users ---
    for user, token in [
        deps_user_platform_manager,
        deps_user_project_owner,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            f"/v1/projects/{project_id}/enable",
            headers=headers,
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_enable_project_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    request: pytest.FixtureRequest,
):
    project_id = deps_project.id

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            f"/v1/projects/{project_id}/enable",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
