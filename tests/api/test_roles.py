import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.role import Role, RoleCreate, RoleUpdate
from any_auth.types.user import UserInDB


def test_api_list_roles_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test listing roles when there are roles in the database.
    """

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            "/roles", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) >= 0
        assert payload["has_more"] is False


def test_api_list_roles_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            "/roles", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_create_role_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [
        deps_user_platform_creator,
        deps_user_platform_manager,
    ]:
        _role_create = RoleCreate(name=deps_fake.word())

        response = test_api_client.post(
            "/roles",
            json=_role_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == _role_create.name, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_create_role_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.post(
            "/roles",
            json=RoleCreate(name=deps_fake.word()).model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_retrieve_role_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_role_na: Role,
):
    """Test retrieving role info."""

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            f"/roles/{deps_role_na.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        retrieved_payload = response.json()
        assert retrieved_payload["id"] == deps_role_na.id
        assert retrieved_payload["name"] == deps_role_na.name


def test_api_retrieve_role_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
    ]:
        response = test_api_client.get(
            "/roles/invalid_role_id", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_retrieve_role_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.get(
            "/roles/any_role_id", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_update_role(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
    deps_role_na: Role,
):
    for user, token in [
        deps_user_platform_manager,
    ]:
        _role_update = RoleUpdate(description=deps_fake.sentence())
        response = test_api_client.post(
            f"/roles/{deps_role_na.id}",
            json=_role_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        updated_payload = response.json()
        assert updated_payload["id"] == deps_role_na.id
        assert updated_payload["description"] == _role_update.description


def test_api_update_role_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [
        deps_user_platform_manager,
    ]:
        response = test_api_client.post(
            "/roles/invalid_role_id",
            json=RoleUpdate(description=deps_fake.sentence()).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_update_role_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
    deps_role_na: Role,
):
    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        _role_update = RoleUpdate(description=deps_fake.sentence())
        response = test_api_client.post(
            f"/roles/{deps_role_na.id}",
            json=_role_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_role(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources

    for user, token in [
        deps_user_platform_manager,
    ]:
        _role_create = RoleCreate(name=deps_fake.word())

        role = backend_client.roles.create(_role_create)
        response = test_api_client.delete(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )

        # Ensure that the role is disabled
        response = test_api_client.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True


def test_api_delete_role_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
    ]:
        response = test_api_client.delete(
            "/roles/invalid_role_id", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_role_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources

    _role_create = RoleCreate(name=deps_fake.word())
    role = backend_client.roles.create(_role_create)

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.delete(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_enable_role(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources

    for user, token in [
        deps_user_platform_manager,
    ]:
        _role_create = RoleCreate(name=deps_fake.word())
        role = backend_client.roles.create(_role_create)
        response = test_api_client.delete(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the role is disabled
        response = test_api_client.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True

        # Enable the role
        response = test_api_client.post(
            f"/roles/{role.id}/enable", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the role is now enabled
        response = test_api_client.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is False


def test_api_enable_role_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
    ]:
        response = test_api_client.post(
            "/roles/invalid_role_id/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_enable_role_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
    deps_backend_client_session_with_all_resources: BackendClient,
):
    backend_client = deps_backend_client_session_with_all_resources

    _role_create = RoleCreate(name=deps_fake.word())
    role = backend_client.roles.create(_role_create)

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        response = test_api_client.post(
            f"/roles/{role.id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
