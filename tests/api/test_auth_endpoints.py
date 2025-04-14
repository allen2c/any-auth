import typing

import pytest
from fastapi.testclient import TestClient

from any_auth.types.oauth2 import TokenResponse
from any_auth.types.user import UserInDB


@pytest.mark.asyncio
async def test_api_auth_login_refresh_token_logout(
    test_api_client: TestClient,
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator_password: typing.Text,
):
    # Test login
    response = test_api_client.post(
        "/login",
        data={
            "username": deps_user_platform_creator[0].email,
            "password": deps_user_platform_creator_password,
        },
    )
    assert response.status_code == 200, response.text

    token = TokenResponse.model_validate_json(response.text)
    assert token.access_token is not None
    assert token.refresh_token is not None

    # Test that the token is valid
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 200, response.text

    # Test refresh token
    response = test_api_client.post(
        "/refresh",
        data={"grant_type": "refresh_token", "refresh_token": token.refresh_token},
    )
    assert response.status_code == 200, response.text
    new_token = TokenResponse.model_validate_json(response.text)
    assert new_token.access_token is not None
    assert new_token.refresh_token is not None
    assert (
        new_token.access_token != token.access_token
    ), "Access token should be different"
    assert (
        new_token.refresh_token != token.refresh_token
    ), "Refresh token should be different"

    # Test that the new token is valid
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {new_token.access_token}"}
    )
    assert response.status_code == 200, response.text

    # Test that the old token is still valid
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 200, response.text

    token = new_token

    # Test logout
    response = test_api_client.post(
        "/logout",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == 204, f"{response.status_code}: {response.text}"

    # Test that the token is invalid after logout
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 401, response.text
