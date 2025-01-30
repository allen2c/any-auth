import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.role import RoleCreate, RoleUpdate
from any_auth.types.user import UserInDB


def test_api_list_roles_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test listing roles when there are roles in the database.
    """

    for user, token in [user_platform_manager, user_platform_creator]:
        response = test_client_module.get(
            "/roles", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) >= 0
        assert payload["has_more"] is False


def test_api_list_roles_denied(
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
            "/roles", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_create_role_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [user_platform_creator, user_platform_manager]:
        _role_create = RoleCreate(name=fake.word())

        response = test_client_module.post(
            "/roles",
            json=_role_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == _role_create.name


def test_api_create_role_denied(
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
            "/roles",
            json=RoleCreate(name=fake.word()).model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_retrieve_role_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    """Test retrieving role info."""
    _role_create = RoleCreate(name=fake.word())
    role = backend_client_session.roles.create(_role_create)

    for user, token in [user_platform_manager, user_platform_creator]:
        response = test_client_module.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        retrieved_payload = response.json()
        assert retrieved_payload["id"] == role.id
        assert retrieved_payload["name"] == role.name


def test_api_retrieve_role_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_platform_manager
    response = test_client_module.get(
        "/roles/invalid_role_id", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_retrieve_role_denied(
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
            "/roles/any_role_id", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_update_role(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    _role_create = RoleCreate(name=fake.word())
    role = backend_client_session.roles.create(_role_create)

    for user, token in [user_platform_manager]:
        _role_update = RoleUpdate(description=fake.sentence())
        response = test_client_module.post(
            f"/roles/{role.id}",
            json=_role_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        updated_payload = response.json()
        assert updated_payload["id"] == role.id
        assert updated_payload["description"] == _role_update.description


def test_api_update_role_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    user, token = user_platform_manager
    response = test_client_module.post(
        "/roles/invalid_role_id",
        json=RoleUpdate(description=fake.sentence()).model_dump(exclude_none=True),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_api_update_role_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    _role_create = RoleCreate(name=fake.word())
    role = backend_client_session.roles.create(_role_create)

    for user, token in [
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        _role_update = RoleUpdate(description=fake.sentence())
        response = test_client_module.post(
            f"/roles/{role.id}",
            json=_role_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_delete_role(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    for user, token in [user_platform_manager]:
        _role_create = RoleCreate(name=fake.word())

        role = backend_client_session.roles.create(_role_create)
        response = test_client_module.delete(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the role is disabled
        response = test_client_module.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True


def test_api_delete_role_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_platform_manager
    response = test_client_module.delete(
        "/roles/invalid_role_id", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_delete_role_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    _role_create = RoleCreate(name=fake.word())
    role = backend_client_session.roles.create(_role_create)

    for user, token in [
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.delete(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_enable_role(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    for user, token in [user_platform_manager]:
        _role_create = RoleCreate(name=fake.word())
        role = backend_client_session.roles.create(_role_create)
        response = test_client_module.delete(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the role is disabled
        response = test_client_module.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True

        # Enable the role
        response = test_client_module.post(
            f"/roles/{role.id}/enable", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the role is now enabled
        response = test_client_module.get(
            f"/roles/{role.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is False


def test_api_enable_role_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_platform_manager
    response = test_client_module.post(
        "/roles/invalid_role_id/enable", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_enable_role_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
    backend_client_session: BackendClient,
):
    _role_create = RoleCreate(name=fake.word())
    role = backend_client_session.roles.create(_role_create)

    for user, token in [
        user_platform_creator,
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.post(
            f"/roles/{role.id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
