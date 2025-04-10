"""
OAuth 2.0 authorization endpoints for AnyAuth.

Implementation of RFC 6749 (OAuth 2.0) authorization server functionality.
"""

import asyncio
import logging
import time
import typing

import fastapi
import fastapi.responses
import fastapi.templating
from fastapi.responses import RedirectResponse

import any_auth.deps.app_state as AppState
import any_auth.utils.oauth2 as oauth2_utils
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.deps.auth import depends_active_user
from any_auth.types.oauth2 import (
    AuthorizationCode,
    CodeChallengeMethod,
    GrantType,
    OAuth2Error,
    OAuth2Token,
    ResponseType,
    TokenRequest,
    TokenResponse,
    TokenType,
)
from any_auth.types.oauth_client import OAuthClient
from any_auth.types.user import UserInDB
from any_auth.utils.oauth2 import build_error_redirect

logger = logging.getLogger(__name__)

router = fastapi.APIRouter(prefix="/oauth2", tags=["OAuth 2.0"])


@router.get("/authorize")
async def authorize(
    response_type: ResponseType = fastapi.Query(...),
    client_id: str = fastapi.Query(...),
    redirect_uri: str = fastapi.Query(...),
    scope: str = fastapi.Query(...),
    state: str | None = fastapi.Query(None),
    code_challenge: str | None = fastapi.Query(None),
    code_challenge_method: CodeChallengeMethod | None = fastapi.Query(None),
    prompt: (
        typing.Literal["none", "login", "consent", "select_account"] | None
    ) = fastapi.Query(None),
    nonce: str | None = fastapi.Query(None),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
) -> fastapi.responses.Response:
    """
    OAuth 2.0 authorization endpoint.
    """
    # 1. Validate client_id
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.retrieve, client_id
    )

    if not oauth_client:
        logger.warning(f"Client ID not found: {client_id}")
        return fastapi.responses.JSONResponse(
            status_code=400,
            content={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Unknown client",
            },
        )

    if oauth_client.disabled:
        logger.warning(f"Client is disabled: {client_id}")
        return fastapi.responses.JSONResponse(
            status_code=400,
            content={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Client is disabled",
            },
        )

    # 2. Validate redirect_uri
    client_redirect_uris = [str(uri) for uri in oauth_client.redirect_uris]
    if not oauth2_utils.validate_redirect_uri(client_redirect_uris, redirect_uri):
        logger.warning(
            f"Invalid redirect URI: {redirect_uri}. " f"Allowed: {client_redirect_uris}"
        )
        return fastapi.responses.JSONResponse(
            status_code=400,
            content={
                "error": OAuth2Error.INVALID_REQUEST,
                "error_description": "Invalid redirect URI",
            },
        )

    # 3. Validate response_type (only 'code' is supported for now)
    if response_type != ResponseType.CODE:
        error_uri = build_error_redirect(
            redirect_uri,
            OAuth2Error.UNSUPPORTED_RESPONSE_TYPE,
            "Only 'code' response type is supported",
            state,
        )
        return RedirectResponse(error_uri)

    # 4. Validate scope - for now, just make sure it's not empty
    if not scope.strip():
        error_uri = build_error_redirect(
            redirect_uri,
            OAuth2Error.INVALID_SCOPE,
            "Scope cannot be empty",
            state,
        )
        return RedirectResponse(error_uri)

    # 5. Validate PKCE parameters if provided
    if code_challenge and not code_challenge_method:
        error_uri = build_error_redirect(
            redirect_uri,
            OAuth2Error.INVALID_REQUEST,
            "code_challenge_method is required when code_challenge is provided",
            state,
        )
        return RedirectResponse(error_uri)

    # 6. Handle 'prompt' parameter (simplified for now)
    # In a real implementation, you would have more logic here to handle
    # different prompt values

    # 7. Generate and store authorization code
    auth_code = AuthorizationCode.model_validate(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "user_id": active_user.id,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "nonce": nonce,
        }
    )

    await asyncio.to_thread(backend_client.oauth2_authorization_codes.create, auth_code)

    # 8. Redirect back to the client with the code
    params = {
        "code": auth_code.code,
    }

    if state:
        params["state"] = state

    redirect_url = oauth2_utils.build_redirect_uri(redirect_uri, params)
    return RedirectResponse(redirect_url)


@router.post("/token")
async def token(
    form_data: TokenRequest = fastapi.Depends(),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
) -> TokenResponse:
    """
    OAuth 2.0 token endpoint.

    Supports the following grant types:
    - authorization_code
    - refresh_token

    Future support planned for:
    - client_credentials
    - password
    """
    # 1. Validate client
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.retrieve, form_data.client_id
    )

    if not oauth_client:
        logger.warning(f"Client ID not found: {form_data.client_id}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Unknown client",
            },
        )

    if oauth_client.disabled:
        logger.warning(f"Client is disabled: {form_data.client_id}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Client is disabled",
            },
        )

    # 2. Authenticate client if client_secret provided
    if (
        oauth_client.client_type == "confidential"
        and form_data.client_secret
        and oauth_client.client_secret != form_data.client_secret
    ):
        logger.warning(f"Invalid client secret for client: {form_data.client_id}")
        raise fastapi.HTTPException(
            status_code=401,
            detail={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Invalid client credentials",
            },
        )

    # 3. Check if the client is allowed to use this grant type
    if not oauth_client.is_grant_type_allowed(form_data.grant_type):
        logger.warning(
            f"Grant type {form_data.grant_type} not allowed for client: "
            + f"{form_data.client_id}"
        )
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.UNAUTHORIZED_CLIENT,
                "error_description": (
                    "Client is not authorized to use "
                    + f"{form_data.grant_type} grant type",
                ),
            },
        )

    # 4. Handle different grant types
    if form_data.grant_type == GrantType.AUTHORIZATION_CODE:
        return await handle_authorization_code_grant(
            form_data, oauth_client, backend_client, settings
        )
    elif form_data.grant_type == GrantType.REFRESH_TOKEN:
        return await handle_refresh_token_grant(
            form_data, oauth_client, backend_client, settings
        )
    elif form_data.grant_type == GrantType.CLIENT_CREDENTIALS:
        # Placeholder for future implementation
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.UNSUPPORTED_GRANT_TYPE,
                "error_description": "Client credentials grant is not supported yet",
            },
        )
    elif form_data.grant_type == GrantType.PASSWORD:
        # Placeholder for future implementation
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.UNSUPPORTED_GRANT_TYPE,
                "error_description": "Password grant is not supported yet",
            },
        )
    else:
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.UNSUPPORTED_GRANT_TYPE,
                "error_description": f"Unsupported grant type: {form_data.grant_type}",
            },
        )


async def handle_authorization_code_grant(
    form_data: TokenRequest,
    oauth_client: OAuthClient,
    backend_client: BackendClient,
    settings: Settings,
) -> TokenResponse:
    """
    Handle the authorization_code grant type.
    """
    # 1. Validate required parameters
    if not form_data.code:
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_REQUEST,
                "error_description": "code is required",
            },
        )

    if not form_data.redirect_uri:
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_REQUEST,
                "error_description": "redirect_uri is required",
            },
        )

    # 2. Retrieve and validate the authorization code
    auth_code = await asyncio.to_thread(
        backend_client.oauth2_authorization_codes.retrieve, form_data.code
    )

    if not auth_code:
        logger.warning(f"Authorization code not found: {form_data.code}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Invalid authorization code",
            },
        )

    # 3. Check if the code is expired
    if auth_code.is_expired():
        logger.warning(f"Authorization code expired: {form_data.code}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Authorization code expired",
            },
        )

    # 4. Check if the code has been used before
    if auth_code.used:
        logger.warning(f"Authorization code already used: {form_data.code}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Authorization code already used",
            },
        )

    # 5. Validate client_id
    if auth_code.client_id != oauth_client.client_id:
        logger.warning(
            f"Client ID mismatch. Expected: {auth_code.client_id}, "
            f"Got: {oauth_client.client_id}"
        )
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Authorization code was not issued for this client",  # noqa: E501
            },
        )

    # 6. Validate redirect_uri
    if str(auth_code.redirect_uri) != form_data.redirect_uri:
        logger.warning(
            f"Redirect URI mismatch. Expected: {auth_code.redirect_uri}, "
            f"Got: {form_data.redirect_uri}"
        )
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "redirect_uri does not match the one used during authorization",  # noqa: E501
            },
        )

    # 7. Validate PKCE code_verifier if PKCE was used
    if auth_code.has_pkce:
        if not form_data.code_verifier:
            logger.warning("code_verifier is required for PKCE")
            raise fastapi.HTTPException(
                status_code=400,
                detail={
                    "error": OAuth2Error.INVALID_REQUEST,
                    "error_description": "code_verifier is required",
                },
            )

        # Verify the code_verifier
        if not await asyncio.to_thread(
            backend_client.oauth2_authorization_codes.validate_code_challenge,
            auth_code,
            form_data.code_verifier,
        ):
            logger.warning("Invalid code_verifier")
            raise fastapi.HTTPException(
                status_code=400,
                detail={
                    "error": OAuth2Error.INVALID_GRANT,
                    "error_description": "Invalid code_verifier",
                },
            )

    # 8. Mark the authorization code as used
    used_auth_code = await asyncio.to_thread(
        backend_client.oauth2_authorization_codes.use_code, form_data.code
    )

    if not used_auth_code:
        logger.warning(f"Failed to mark code as used: {form_data.code}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.SERVER_ERROR,
                "error_description": "Failed to process authorization code",
            },
        )

    # 9. Generate access token and refresh token
    now = int(time.time())
    token = OAuth2Token(
        user_id=auth_code.user_id,
        client_id=oauth_client.client_id,
        scope=auth_code.scope,
        expires_at=now + settings.TOKEN_EXPIRATION_TIME,
        authorization_code_id=auth_code.id,
    )

    # Save the token
    await asyncio.to_thread(backend_client.oauth2_tokens.create, token)

    # 10. Prepare the response
    token_response = TokenResponse(
        access_token=token.access_token,
        token_type=TokenType.BEARER,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        refresh_token=token.refresh_token,
        scope=token.scope,
    )

    return token_response


async def handle_refresh_token_grant(
    form_data: TokenRequest,
    oauth_client: OAuthClient,
    backend_client: BackendClient,
    settings: Settings,
) -> TokenResponse:
    """
    Handle the refresh_token grant type to issue a new access token.
    """

    # 1. Validate required parameters
    if not form_data.refresh_token:
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_REQUEST,
                "error_description": "refresh_token is required",
            },
        )

    # 2. Retrieve and validate the refresh token
    token = await asyncio.to_thread(
        backend_client.oauth2_tokens.retrieve_by_refresh_token, form_data.refresh_token
    )

    if not token:
        logger.warning(f"Refresh token not found: {form_data.refresh_token}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Invalid refresh token",
            },
        )

    # 3. Check if the token is revoked
    if token.revoked:
        logger.warning(f"Refresh token has been revoked: {form_data.refresh_token}")
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Refresh token has been revoked",
            },
        )

    # 4. Check if the client IDs match
    if token.client_id != oauth_client.client_id:
        logger.warning(
            f"Client ID mismatch. Expected: {token.client_id}, "
            f"Got: {oauth_client.client_id}"
        )
        raise fastapi.HTTPException(
            status_code=400,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Refresh token was not issued for this client",
            },
        )

    # 5. Handle scope parameter - restrict to originally granted scopes
    requested_scope = form_data.scope
    original_scope = token.scope

    if requested_scope:
        # If a scope parameter is included, verify it doesn't ask for more permissions
        requested_scopes = requested_scope.split()
        original_scopes = original_scope.split()

        # Make sure all requested scopes were in the original token
        if not all(scope in original_scopes for scope in requested_scopes):
            raise fastapi.HTTPException(
                status_code=400,
                detail={
                    "error": OAuth2Error.INVALID_SCOPE,
                    "error_description": "Requested scope exceeds original grant",
                },
            )
        final_scope = requested_scope
    else:
        # If no scope parameter is included, use the original scope
        final_scope = original_scope

    # 6. Generate new access token (and optionally new refresh token)
    now = int(time.time())
    new_token = OAuth2Token(
        user_id=token.user_id,
        client_id=oauth_client.client_id,
        scope=final_scope,
        expires_at=now + settings.TOKEN_EXPIRATION_TIME,
        # Optionally keep reference to original authorization code
        # if needed for auditing
        authorization_code_id=token.authorization_code_id,
    )

    # Save the new token
    await asyncio.to_thread(backend_client.oauth2_tokens.create, new_token)

    # 7. Optionally invalidate old token (depends on your token rotation policy)
    # Uncomment if you want to revoke the old refresh token
    # await asyncio.to_thread(
    #    backend_client.oauth2_tokens.revoke_token, form_data.refresh_token
    # )

    # 8. Prepare the response
    token_response = TokenResponse(
        access_token=new_token.access_token,
        token_type=TokenType.BEARER,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        refresh_token=new_token.refresh_token,
        scope=new_token.scope,
    )

    return token_response


@router.post("/revoke")
async def revoke_token(
    token: str = fastapi.Form(...),
    token_type_hint: (
        typing.Literal["access_token", "refresh_token"] | None
    ) = fastapi.Form(None),
    client_id: str = fastapi.Form(...),
    client_secret: str | None = fastapi.Form(None),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> fastapi.responses.Response:
    """
    OAuth 2.0 token revocation endpoint (RFC 7009).
    """
    # 1. Validate and authenticate client
    oauth_client = await asyncio.to_thread(
        backend_client.oauth_clients.retrieve, client_id
    )

    if not oauth_client:
        logger.warning(f"Client ID not found: {client_id}")
        raise fastapi.HTTPException(
            status_code=401,
            detail={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Unknown client",
            },
        )

    if oauth_client.disabled:
        logger.warning(f"Client is disabled: {client_id}")
        raise fastapi.HTTPException(
            status_code=401,
            detail={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Client is disabled",
            },
        )

    # Authenticate client if client_secret provided
    if oauth_client.client_secret and client_secret != oauth_client.client_secret:
        logger.warning(f"Invalid client secret for client: {client_id}")
        raise fastapi.HTTPException(
            status_code=401,
            detail={
                "error": OAuth2Error.INVALID_CLIENT,
                "error_description": "Invalid client credentials",
            },
        )

    # 2. Revoke the token
    # The spec requires us to respond with 200 OK even if the token doesn't exist
    await asyncio.to_thread(
        backend_client.oauth2_tokens.revoke_token,
        token,
        token_type_hint,
    )

    # 3. Return success response
    return fastapi.responses.Response(status_code=200)
