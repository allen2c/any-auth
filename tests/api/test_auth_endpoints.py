import typing

import pytest
from fastapi.testclient import TestClient

from any_auth.types.oauth2 import TokenResponse
from any_auth.types.oauth_client import OAuthClient
from any_auth.types.user import UserInDB


@pytest.mark.asyncio
async def test_api_auth_oauth2_flow(
    test_api_client: TestClient,
    deps_oauth_clients: "OAuthClient",
    deps_user_platform_creator: typing.Tuple[UserInDB, typing.Text],
    deps_user_platform_creator_password: typing.Text,
):
    assert deps_oauth_clients.client_secret is not None

    # Test OAuth2 password grant (RFC 6749 section 4.3)
    response = test_api_client.post(
        "/oauth2/token",
        data={
            "grant_type": "password",
            "username": deps_user_platform_creator[0].email,
            "password": deps_user_platform_creator_password,
            "client_id": deps_oauth_clients.client_id,
            "client_secret": deps_oauth_clients.client_secret,
            "scope": "openid email profile",
        },
    )
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

    token = TokenResponse.model_validate_json(response.text)
    assert token.access_token is not None
    assert token.refresh_token is not None
    assert token.token_type == "Bearer"
    assert token.expires_in > 0

    # Test that the token is valid
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

    # Test OpenID Connect userinfo endpoint
    response = test_api_client.get(
        "/oauth2/userinfo", headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
    user_info = response.json()
    assert user_info["sub"] == deps_user_platform_creator[0].id

    # Test refresh token grant (RFC 6749 section 6)
    response = test_api_client.post(
        "/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": "ropc_login_client",
            "scope": "openid email profile",
        },
    )
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
    new_token = TokenResponse.model_validate_json(response.text)
    assert new_token.access_token is not None
    assert new_token.refresh_token is not None
    assert (
        new_token.access_token != token.access_token
    ), "Access token should be different"

    # Test that the new token is valid
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {new_token.access_token}"}
    )
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

    # Test token revocation (RFC 7009)
    response = test_api_client.post(
        "/oauth2/revoke",
        data={
            "token": new_token.access_token,
            "token_type_hint": "access_token",
            "client_id": "ropc_login_client",
            "client_secret": deps_oauth_clients.client_secret,
        },
    )
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

    # Test that the token is invalid after revocation
    response = test_api_client.get(
        "/me", headers={"Authorization": f"Bearer {new_token.access_token}"}
    )
    assert response.status_code == 401, f"Got {response.status_code}: {response.text}"
