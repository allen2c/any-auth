import typing

from fastapi.testclient import TestClient

from any_auth.types.user import UserInDB


def test_api_health(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
):
    """
    Test the health check endpoint.
    """
    response = test_client_module.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_me(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_platform_manager: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test retrieving the current user information.
    """
    user, token = user_platform_manager
    response = test_client_module.get(
        "/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == user.id


def test_api_me_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
):
    """
    Test unauthorized access to the /me endpoint.
    """
    response = test_client_module.get("/me")
    assert response.status_code == 401


def test_api_me_organizations(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_org_owner: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test retrieving the organizations of the current user.
    """
    user, token = user_org_owner
    response = test_client_module.get(
        "/me/organizations", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["object"] == "list"
    assert len(response.json()["data"]) > 0
    assert response.json()["has_more"] is False


def test_api_me_organizations_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
):
    """
    Test unauthorized access to the /me/organizations endpoint.
    """
    response = test_client_module.get("/me/organizations")
    assert response.status_code == 401


def test_api_me_projects(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
    user_project_owner: typing.Tuple[UserInDB, typing.Text],
):
    """
    Test retrieving the projects of the current user.
    """
    user, token = user_project_owner
    response = test_client_module.get(
        "/me/projects", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["object"] == "list"
    assert len(response.json()["data"]) >= 0
    assert response.json()["has_more"] is False


def test_api_me_projects_denied(
    raise_if_not_test_env: None,
    test_client_module: TestClient,
):
    """
    Test unauthorized access to the /me/projects endpoint.
    """
    response = test_client_module.get("/me/projects")
    assert response.status_code == 401
