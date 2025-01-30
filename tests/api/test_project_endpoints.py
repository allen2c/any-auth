import typing

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import Organization
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate
from any_auth.types.user import UserInDB


# --- Test Allowed Users ---
def test_api_list_projects_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["object"] == "list"


# --- Test Denied Users ---
def test_api_list_projects_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id

    for user, token in [
        user_project_owner,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Create Project ---
def test_api_create_project_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
):
    organization_id = org_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
    ]:
        _project_create = ProjectCreate.fake(fake)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects",
            json=_project_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["name"] == _project_create.name


# --- Test Create Project Denied ---
def test_api_create_project_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    fake: Faker,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id

    for user, token in [
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        _project_create = ProjectCreate.fake(fake)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects",
            json=_project_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Retrieve Project ---
def test_api_retrieve_project_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["id"] == project_id


# --- Test Retrieve Project Denied ---
def test_api_retrieve_project_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Update Project ---
def test_api_update_project_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    fake: Faker,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_platform_manager,
        user_org_owner,
        user_org_editor,
        user_project_owner,
        user_project_editor,
    ]:
        _project_update = ProjectUpdate(full_name=fake.company())
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}",
            json=_project_update.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["id"] == project_id
        assert payload["full_name"] == _project_update.full_name


# --- Test Update Project Denied ---
def test_api_update_project_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    fake: Faker,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_platform_creator,
        user_org_viewer,
        user_project_viewer,
        user_newbie,
    ]:
        _project_update = ProjectUpdate(full_name=fake.company())
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}",
            json=_project_update.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


# --- Test Delete Project ---
def test_api_delete_project_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    fake: Faker,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_platform_manager,
        user_org_owner,
        user_org_editor,
        user_project_owner,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.delete(
            f"/organizations/{organization_id}/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )

    # Recover the project
    headers = {"Authorization": f"Bearer {user_platform_manager[1]}"}
    response = test_client_module.post(
        f"/organizations/{organization_id}/projects/{project_id}/enable",
        headers=headers,
    )
    assert response.status_code == 204, "Project should be recovered"


# --- Test Delete Project Denied ---
def test_api_delete_project_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_platform_creator,
        user_org_viewer,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.delete(
            f"/organizations/{organization_id}/projects/{project_id}",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


def test_api_enable_project_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    # --- Test Allowed Users ---
    for user, token in [
        user_platform_manager,
        user_org_owner,
        user_org_editor,
        user_project_owner,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}/enable",
            headers=headers,
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )


def test_api_enable_project_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_platform_creator,
        user_org_viewer,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}/enable",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


def test_api_list_project_members_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    # --- Test Allowed Users ---
    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects/{project_id}/members",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["object"] == "list"


def test_api_list_project_members_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    for user, token in [
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects/{project_id}/members",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


def test_api_create_project_member_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id
    user_id = user_newbie[0].id
    _member_create = ProjectMemberCreate(user_id=user_id)

    # --- Test Allowed Users ---
    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_project_owner,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["user_id"] == user_id


def test_api_create_project_member_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id
    user_id = user_newbie[0].id
    _member_create = ProjectMemberCreate(user_id=user_id)

    for user, token in [
        user_org_viewer,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}/members",
            json=_member_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


def test_api_retrieve_project_member_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    backend_client_session: BackendClient,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id
    project_members_list: list[ProjectMember] = (
        backend_client_session.project_members.list(project_id=project_id).data
    )
    assert len(project_members_list) > 0
    member_id = project_members_list[0].id

    # --- Test Allowed Users ---
    for user, token in [
        user_platform_manager,
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects/{project_id}/members/{member_id}",  # noqa: E501
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )
        payload = response.json()
        assert payload["id"] == member_id


def test_api_retrieve_project_member_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    # --- Test Denied Users ---
    for user, token in [
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_client_module.get(
            f"/organizations/{organization_id}/projects/{project_id}/members/any_member_id",  # noqa: E501
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )


def test_api_delete_project_member_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id

    # --- Test Allowed Users ---
    for user, token in [
        user_platform_manager,
        user_org_owner,
        user_org_editor,
        user_project_owner,
    ]:
        # Create a member to delete
        create_member_response = test_client_module.post(
            f"/organizations/{organization_id}/projects/{project_id}/members",
            json=ProjectMemberCreate(user_id=user_newbie[0].id).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {user_project_owner[1]}"},
        )
        assert create_member_response.status_code == 200
        member_id_to_delete = create_member_response.json()["id"]

        response = test_client_module.delete(
            f"/organizations/{organization_id}/projects/{project_id}/members/{member_id_to_delete}",  # noqa: E501
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}"
        )


def test_api_delete_project_member_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    user_newbie: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    org_of_session: Organization,
    project_of_session: Project,
    request: pytest.FixtureRequest,
):
    organization_id = org_of_session.id
    project_id = project_of_session.id
    project_members_list: list[ProjectMember] = (
        backend_client_session_with_roles.project_members.list(
            project_id=project_id
        ).data
    )
    assert len(project_members_list) > 0

    # --- Test Denied Users ---
    for user, token in [
        user_platform_creator,
        user_org_viewer,
        user_project_editor,
        user_project_viewer,
        user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        response = test_client_module.delete(
            f"/organizations/{organization_id}/projects/{project_id}/members/{project_members_list[0].id}",  # noqa: E501
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}"
        )
