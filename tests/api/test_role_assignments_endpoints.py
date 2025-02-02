import typing

from faker import Faker
from fastapi.testclient import TestClient

from any_auth.backend import BackendClient
from any_auth.types.organization import Organization
from any_auth.types.project import Project
from any_auth.types.role import PLATFORM_CREATOR_ROLE
from any_auth.types.role_assignment import RoleAssignmentCreate
from any_auth.types.user import UserInDB


def test_api_create_role_assignment_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    fake: Faker,
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    target_role = backend_client_session_with_roles.roles.retrieve_by_id_or_name(
        PLATFORM_CREATOR_ROLE.name
    )
    assert target_role is not None

    for user, token in [user_platform_manager, user_platform_creator]:
        _role_assignment_create = RoleAssignmentCreate(
            user_id=user_newbie[0].id,
            role_id=target_role.id,
            resource_id=project_of_session.id,
        )

        response = test_client_module.post(
            "/role-assignments",
            json=_role_assignment_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == _role_assignment_create.user_id
        assert payload["role_id"] == _role_assignment_create.role_id
        assert payload["resource_id"] == _role_assignment_create.resource_id


def test_api_create_role_assignment_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    fake: Faker,
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    role = backend_client_session_with_roles.roles.list(limit=1).data[0]

    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        _role_assignment_create = RoleAssignmentCreate(
            user_id=user_newbie[0].id,
            role_id=role.id,
            resource_id=project_of_session.id,
        )
        response = test_client_module.post(
            "/role-assignments",
            json=_role_assignment_create.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_retrieve_role_assignment_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    fake: Faker,
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    role = backend_client_session_with_roles.roles.list(limit=1).data[0]
    _role_assignment_create = RoleAssignmentCreate(
        user_id=user_newbie[0].id,
        role_id=role.id,
        resource_id=project_of_session.id,
    )
    role_assignment = backend_client_session_with_roles.role_assignments.create(
        _role_assignment_create
    )

    for user, token in [user_platform_manager, user_platform_creator]:
        response = test_client_module.get(
            f"/role-assignments/{role_assignment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == role_assignment.id


def test_api_retrieve_role_assignment_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    fake: Faker,
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
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
            "/role-assignments/any_role_assignment_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


def test_api_delete_role_assignment_allowed(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
    user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    fake: Faker,
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    role = backend_client_session_with_roles.roles.list(limit=1).data[0]
    for user, token in [user_platform_manager, user_platform_creator]:
        _role_assignment_create = RoleAssignmentCreate(
            user_id=user_newbie[0].id,
            role_id=role.id,
            resource_id=project_of_session.id,
        )
        _role_assignment_created = (
            backend_client_session_with_roles.role_assignments.create(
                _role_assignment_create
            )
        )

        response = test_client_module.delete(
            f"/role-assignments/{_role_assignment_created.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204


def test_api_delete_role_assignment_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
    user_org_editor: typing.Tuple[UserInDB, typing.Text],
    user_org_viewer: typing.Tuple[UserInDB, typing.Text],
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
    user_project_editor: typing.Tuple[UserInDB, typing.Text],
    user_project_viewer: typing.Tuple[UserInDB, typing.Text],
    backend_client_session_with_roles: BackendClient,
    fake: Faker,
    org_of_session: Organization,
    project_of_session: Project,
    user_newbie: typing.Tuple[UserInDB, typing.Text],
):
    for user, token in [
        user_org_owner,
        user_org_editor,
        user_org_viewer,
        user_project_owner,
        user_project_editor,
        user_project_viewer,
    ]:
        response = test_client_module.delete(
            "/role-assignments/any_role_assignment_id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
