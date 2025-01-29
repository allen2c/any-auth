import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.types.project import Project
from any_auth.types.user import UserCreate, UserInDB, UserUpdate


def test_api_list_users(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test listing users when there are no users in the database.
    """

    for user, token in [user_platform_manager, user_platform_creator]:
        response = test_client_module.get(
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
            "/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_create_user(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [user_platform_creator, user_platform_manager]:
        _user_create = UserCreate.fake(fake)

        response = test_client_module.post(
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
            "/users",
            json=UserCreate.fake(fake).model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_retrieve_user(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    """Test retrieving user info."""

    for user, token in [user_platform_manager, user_platform_creator]:

        response = test_client_module.get(
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
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_platform_manager
    response = test_client_module.get(
        "/users/invalid_user_id", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_retrieve_user_denied(
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
            f"/users/{user.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_update_user(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [user_platform_manager]:
        _user_update = UserUpdate(phone=fake.phone_number())
        response = test_client_module.post(
            f"/users/{user.id}",
            json=_user_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        updated_payload = response.json()
        assert updated_payload["id"] == user.id
        assert updated_payload["phone"] == _user_update.phone


def test_api_update_user_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    user, token = user_platform_manager
    response = test_client_module.post(
        "/users/invalid_user_id",
        json=UserUpdate(phone=fake.phone_number()).model_dump(exclude_none=True),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_api_update_user_denied(
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
):
    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        _user_update = UserUpdate(phone=fake.phone_number())
        response = test_client_module.post(
            f"/users/{user.id}",
            json=_user_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_delete_user(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [user_platform_manager]:
        _user_create = UserCreate.fake(fake)

        response = test_client_module.post(
            "/users",
            json=_user_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        user_id = payload["id"]
        response = test_client_module.delete(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the user is disabled
        response = test_client_module.get(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True


def test_api_delete_user_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_platform_manager
    response = test_client_module.delete(
        "/users/invalid_user_id", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_delete_user_denied(
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
):
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
            f"/users/{user.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


def test_api_enable_user(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [user_platform_manager]:

        _user_create = UserCreate.fake(fake)
        response = test_client_module.post(
            "/users",
            json=_user_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        user_id = payload["id"]
        response = test_client_module.delete(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the user is disabled
        response = test_client_module.get(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is True

        # Enable the user
        response = test_client_module.post(
            f"/users/{user_id}/enable", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Ensure that the user is now enabled
        response = test_client_module.get(
            f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["disabled"] is False


def test_api_enable_user_not_found(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    user, token = user_platform_manager
    response = test_client_module.post(
        "/users/invalid_user_id/enable", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_api_enable_user_denied(
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
):
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
            f"/users/{user.id}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_list_user_role_assignments(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    project_of_session: Project,
    fake: Faker,
):
    project_id = project_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
    ]:
        response = test_client_module.get(
            f"/users/{user.id}/role-assignments",
            headers={"Authorization": f"Bearer {token}"},
            params={"project_id": project_id},
        )
        assert response.status_code == 200
        assignments_payload = response.json()
        assert assignments_payload["object"] == "list"
        assert len(assignments_payload["data"]) >= 0
        assert assignments_payload["has_more"] is False


def test_api_list_user_role_assignments_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    project_of_session: Project,
    fake: Faker,
):
    project_id = project_of_session.id

    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.get(
            f"/users/{user.id}/role-assignments",
            headers={"Authorization": f"Bearer {token}"},
            params={"project_id": project_id},
        )
        assert response.status_code == 403


def test_api_list_user_roles(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    project_of_session: Project,
    fake: Faker,
):
    project_id = project_of_session.id

    for user, token in [
        user_platform_manager,
        user_platform_creator,
    ]:
        response = test_client_module.get(
            f"/users/{user.id}/roles",
            headers={"Authorization": f"Bearer {token}"},
            params={"project_id": project_id},
        )
        assert response.status_code == 200
        roles_payload = response.json()
        assert roles_payload["object"] == "list"
        assert len(roles_payload["data"]) >= 0
        assert roles_payload["has_more"] is False


def test_api_list_user_roles_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    project_of_session: Project,
    fake: Faker,
):
    project_id = project_of_session.id

    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.get(
            f"/users/{user.id}/roles",
            headers={"Authorization": f"Bearer {token}"},
            params={"project_id": project_id},
        )
        assert response.status_code == 403


def test_api_list_user_organizations(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [
        user_platform_manager,
        user_platform_creator,
    ]:
        response = test_client_module.get(
            f"/users/{user.id}/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        organizations_payload = response.json()
        assert organizations_payload["object"] == "list"
        assert len(organizations_payload["data"]) >= 0
        assert organizations_payload["has_more"] is False


def test_api_list_user_organizations_denied(
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
        response = test_client_module.get(
            f"/users/{user.id}/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_list_user_projects(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    fake: Faker,
):
    for user, token in [
        user_platform_manager,
        user_platform_creator,
    ]:
        response = test_client_module.get(
            f"/users/{user.id}/projects", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        projects_payload = response.json()
        assert projects_payload["object"] == "list"
        assert len(projects_payload["data"]) >= 0
        assert projects_payload["has_more"] is False


def test_api_list_user_projects_denied(
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
        response = test_client_module.get(
            f"/users/{user.id}/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
