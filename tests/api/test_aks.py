import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.api_key import APIKeyCreate, APIKeyUpdate
from any_auth.types.project import Project
from any_auth.types.user import UserInDB


def test_api_list_api_keys_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            "/v1/api-keys", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["object"] == "list"


def test_api_list_api_keys_denied(
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
        response = test_api_client.get(
            "/v1/api-keys", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_create_api_key_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_fake: Faker,
):
    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        api_key_create = APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        )

        params = {
            "created_by": user.id,
            "resource_id": deps_project.id,
        }

        response = test_api_client.post(
            "/v1/api-keys",
            params=params,
            json=api_key_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["name"] == api_key_create.name
        assert payload["description"] == api_key_create.description


def test_api_create_api_key_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
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
        api_key_create = APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        )

        params = {
            "created_by": user.id,
            "resource_id": deps_project.id,
        }

        response = test_api_client.post(
            "/v1/api-keys",
            params=params,
            json=api_key_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_retrieve_api_key_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_project: Project,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create an API key to retrieve
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        created_by=user.id,
        resource_id=deps_project.id,
    )

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
    ]:
        response = test_api_client.get(
            f"/v1/api-keys/{api_key.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["id"] == api_key.id
        assert payload["name"] == api_key.name
        assert payload["description"] == api_key.description


def test_api_retrieve_api_key_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create an API key to retrieve
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        created_by=user.id,
        resource_id=deps_project.id,
    )

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        response = test_api_client.get(
            f"/v1/api-keys/{api_key.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_update_api_key_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_project: Project,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    user, token = deps_user_platform_manager

    # Create an API key to update
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        created_by=user.id,
        resource_id=deps_project.id,
    )

    # Update the API key
    api_key_update = APIKeyUpdate(
        name=deps_fake.word(),
        description=deps_fake.sentence(),
    )

    response = test_api_client.put(
        f"/v1/api-keys/{api_key.id}",
        json=api_key_update.model_dump(exclude_none=True),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, (
        f"User fixture '{user.model_dump_json()}' should be allowed, "
        + f"but got {response.status_code}: {response.text}"
    )
    payload = response.json()
    assert payload["id"] == api_key.id
    assert payload["name"] == api_key_update.name
    assert payload["description"] == api_key_update.description


def test_api_update_api_key_denied(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_project: Project,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    platform_user, _ = deps_user_platform_manager

    # Create an API key to update
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        created_by=platform_user.id,
        resource_id=deps_project.id,
    )

    # Try to update with different users
    api_key_update = APIKeyUpdate(
        name=deps_fake.word(),
        description=deps_fake.sentence(),
    )

    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        response = test_api_client.put(
            f"/v1/api-keys/{api_key.id}",
            json=api_key_update.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_api_key_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_project: Project,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    user, token = deps_user_platform_manager

    # Create an API key to delete
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        created_by=user.id,
        resource_id=deps_project.id,
    )

    # Delete the API key
    response = test_api_client.delete(
        f"/v1/api-keys/{api_key.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204, (
        f"User fixture '{user.model_dump_json()}' should be allowed, "
        + f"but got {response.status_code}: {response.text}"
    )

    # Verify the API key is deleted
    retrieved_api_key = backend_client.api_keys.retrieve(api_key.id)
    assert retrieved_api_key is None


def test_api_delete_api_key_denied(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_project: Project,
    deps_fake: Faker,
):
    backend_client = deps_backend_client_session_with_all_resources
    platform_user, _ = deps_user_platform_manager

    # Create an API key to delete
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        created_by=platform_user.id,
        resource_id=deps_project.id,
    )

    # Try to delete with different users
    for user, token in [
        deps_user_platform_creator,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_newbie,
    ]:
        response = test_api_client.delete(
            f"/v1/api-keys/{api_key.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
