import typing

from fastapi.testclient import TestClient

from any_auth.types.user import UserInDB


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
