import typing

from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.api_key import APIKeyCreate
from any_auth.types.project import Project
from any_auth.types.role import Role
from any_auth.types.role_assignment import (
    APIKeyRoleAssignmentCreate,
    RoleAssignmentCreate,
)
from any_auth.types.user import UserInDB


def test_api_retrieve_project_api_key_role_assignments_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_fake: typing.Any,
):
    """Test retrieving role assignments for a project API key (allowed users)."""
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create a test API key
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        user_id=user.id,
        resource_id=project_id,
    )

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
        deps_user_project_editor,
        deps_user_project_viewer,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/projects/{project_id}/api-keys/{api_key.id}/role-assignments",
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["object"] == "list"


def test_api_retrieve_project_api_key_role_assignments_denied(
    test_api_client: TestClient,
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: typing.Any,
):
    """Test retrieving role assignments for a project API key (denied users)."""
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create a test API key
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        user_id=user.id,
        resource_id=project_id,
    )

    for user, token in [
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.get(
            f"/projects/{project_id}/api-keys/{api_key.id}/role-assignments",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_create_project_api_key_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_role_na: "Role",
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_fake: typing.Any,
):
    """Test creating a role assignment for a project API key (allowed users)."""
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create a test API key
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        user_id=user.id,
        resource_id=project_id,
    )

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
    ]:
        role_assignment_create = APIKeyRoleAssignmentCreate(
            role=deps_role_na.name,
        )

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            f"/projects/{project_id}/api-keys/{api_key.id}/role-assignments",
            json=role_assignment_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 200, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )
        payload = response.json()
        assert payload["target_id"] == api_key.id
        assert payload["role_id"] == deps_role_na.id
        assert payload["resource_id"] == project_id


def test_api_create_project_api_key_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_role_na: "Role",
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: typing.Any,
):
    """Test creating a role assignment for a project API key (denied users)."""
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create a test API key
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        user_id=user.id,
        resource_id=project_id,
    )

    for user, token in [
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        role_assignment_create = APIKeyRoleAssignmentCreate(
            role=deps_role_na.name,
        )

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.post(
            f"/projects/{project_id}/api-keys/{api_key.id}/role-assignments",
            json=role_assignment_create.model_dump(exclude_none=True),
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_project_api_key_role_assignment_allowed(
    test_api_client: TestClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_owner: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_role_na: "Role",
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_fake: typing.Any,
):
    """Test deleting a role assignment for a project API key (allowed users)."""
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create a test API key
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        user_id=user.id,
        resource_id=project_id,
    )

    for user, token in [
        deps_user_platform_manager,
        deps_user_platform_creator,
        deps_user_project_owner,
    ]:
        # Create a role assignment to delete
        role_assignment_create = RoleAssignmentCreate(
            target_id=api_key.id,
            role_id=deps_role_na.id,
            resource_id=project_id,
        )
        role_assignment = backend_client.role_assignments.create(role_assignment_create)

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.delete(
            f"/projects/{project_id}/api-keys/{api_key.id}/role-assignments/{role_assignment.id}",  # noqa: E501
            headers=headers,
        )
        assert response.status_code == 204, (
            f"User fixture '{user.model_dump_json()}' should be allowed, "
            + f"but got {response.status_code}: {response.text}"
        )


def test_api_delete_project_api_key_role_assignment_denied(
    test_api_client: TestClient,
    deps_user_project_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_owner: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_editor: typing.Tuple[UserInDB, typing.Text],
    deps_user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_project: Project,
    deps_role_na: "Role",
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    deps_fake: typing.Any,
):
    """Test deleting a role assignment for a project API key (denied users)."""
    project_id = deps_project.id
    backend_client = deps_backend_client_session_with_all_resources
    user, _ = deps_user_platform_manager

    # Create a test API key
    api_key = backend_client.api_keys.create(
        APIKeyCreate(
            name=deps_fake.word(),
            description=deps_fake.sentence(),
        ),
        user_id=user.id,
        resource_id=project_id,
    )

    # Create a role assignment to attempt to delete
    role_assignment_create = RoleAssignmentCreate(
        target_id=api_key.id,
        role_id=deps_role_na.id,
        resource_id=project_id,
    )
    role_assignment = backend_client.role_assignments.create(role_assignment_create)

    for user, token in [
        deps_user_project_editor,
        deps_user_project_viewer,
        deps_user_org_owner,
        deps_user_org_editor,
        deps_user_org_viewer,
        deps_user_newbie,
    ]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = test_api_client.delete(
            f"/projects/{project_id}/api-keys/{api_key.id}/role-assignments/{role_assignment.id}",  # noqa: E501
            headers=headers,
        )
        assert response.status_code == 403, (
            f"User fixture '{user.model_dump_json()}' should be denied, "
            + f"but got {response.status_code}: {response.text}"
        )
