import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.types.user import UserCreate, UserInDB, UserUpdate


# === Endpoint: /users ===
def test_api_list_users(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test listing users when there are no users in the database.
    """

    for _, token in [deps_user_platform_manager, deps_user_platform_creator]:
        response = test_api_client.get(
            "/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) > 0
        assert payload["has_more"] is False
        assert payload["first_id"] == payload["data"][0]["id"]
        assert payload["last_id"] == payload["data"][-1]["id"]


def test_api_list_users_denied(
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
            "/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


# === End of Endpoint: /users ===


# === Endpoint: /users/{user_id} ===


def test_api_create_user(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for _, token in [deps_user_platform_creator, deps_user_platform_manager]:
        _user_create = UserCreate.fake(deps_fake)

        response = test_api_client.post(
            "/users",
            json=_user_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["username"] == _user_create.username
        assert payload["full_name"] == _user_create.full_name
        assert payload["email"] == _user_create.email
        assert payload["phone"] == _user_create.phone
        assert payload["metadata"] == _user_create.metadata


def test_api_create_user_denied(
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
            "/users",
            json=UserCreate.fake(deps_fake).model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id} ===


# === Endpoint: /users/{user_id} ===


def test_api_retrieve_user(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """Test retrieving user info."""

    for user, token in [deps_user_platform_manager, deps_user_platform_creator]:

        response = test_api_client.get(
            f"/users/{user.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        retrieved_payload = response.json()
        assert retrieved_payload["id"] == user.id
        assert retrieved_payload["username"] == user.username
        assert retrieved_payload["full_name"] == user.full_name
        assert retrieved_payload["email"] == user.email
        assert retrieved_payload["phone"] == user.phone
        assert retrieved_payload["metadata"] == user.metadata


def test_api_retrieve_user_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = deps_user_platform_manager
    response = test_api_client.get(
        "/users/invalid_user_id", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_retrieve_user_denied(
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
            f"/users/{user.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id} ===


# === Endpoint: /users/{user_id} ===


def test_api_update_user(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [deps_user_platform_manager]:
        _user_update = UserUpdate(phone=deps_fake.phone_number())
        response = test_api_client.put(
            f"/users/{user.id}",
            json=_user_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        updated_payload = response.json()
        assert updated_payload["id"] == user.id
        assert updated_payload["phone"] == _user_update.phone


def test_api_update_user_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for _, token in [deps_user_platform_manager]:
        response = test_api_client.put(
            "/users/invalid_user_id",
            json=UserUpdate(phone=deps_fake.phone_number()).model_dump(
                exclude_none=True
            ),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 404


def test_api_update_user_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
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
        _user_update = UserUpdate(phone=deps_fake.phone_number())
        response = test_api_client.put(
            f"/users/{user.id}",
            json=_user_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id} ===


# === Endpoint: /users/{user_id} ===


def test_api_delete_user(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for user, token in [deps_user_platform_manager]:
        _user_create = UserCreate.fake(deps_fake)

        response = test_api_client.post(
            "/users",
            json=_user_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        user_id = payload["id"]
        response = test_api_client.delete(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the user is disabled
        response = test_api_client.get(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True


def test_api_delete_user_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    _, token = deps_user_platform_manager
    response = test_api_client.delete(
        "/users/invalid_user_id", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_delete_user_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
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
        response = test_api_client.delete(
            f"/users/{user.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id} ===


# === Endpoint: /users/{user_id}/enable ===


def test_api_enable_user(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: Faker,
):
    for _, token in [deps_user_platform_manager]:

        _user_create = UserCreate.fake(deps_fake)
        response = test_api_client.post(
            "/users",
            json=_user_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        user_id = payload["id"]
        response = test_api_client.delete(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the user is disabled
        response = test_api_client.get(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True

        # Enable the user
        response = test_api_client.post(
            f"/users/{user_id}/enable", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the user is now enabled
        response = test_api_client.get(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is False


def test_api_enable_user_not_found(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    _, token = deps_user_platform_manager
    response = test_api_client.post(
        "/users/invalid_user_id/enable", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_enable_user_denied(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
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
        response = test_api_client.post(
            f"/users/{user.id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id}/enable ===


# === Endpoint: /users/{user_id}/organizations ===


def test_api_list_user_organizations(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            f"/users/{user.id}/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        organizations_payload = response.json()
        assert organizations_payload["object"] == "list"
        assert len(organizations_payload["data"]) >= 0
        assert organizations_payload["has_more"] is False


def test_api_list_user_organizations_denied(
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
            f"/users/{user.id}/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id}/organizations ===


# === Endpoint: /users/{user_id}/projects ===


def test_api_list_user_projects(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            f"/users/{user.id}/projects", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        projects_payload = response.json()
        assert projects_payload["object"] == "list"
        assert len(projects_payload["data"]) >= 0
        assert projects_payload["has_more"] is False


def test_api_list_user_projects_denied(
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
            f"/users/{user.id}/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# === End of Endpoint: /users/{user_id}/projects ===
