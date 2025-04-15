import asyncio
import logging
import time
import typing
import uuid

import diskcache
import fastapi
import redis
from fastapi.security import OAuth2PasswordRequestForm

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
import any_auth.utils.is_ as IS
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.deps.auth import depends_active_user, oauth2_scheme
from any_auth.types.auth import AuthTokenRequest
from any_auth.types.oauth2 import OAuth2Error, OAuth2Token, TokenResponse, TokenType
from any_auth.types.role import Permission, Role
from any_auth.types.user import UserCreate, UserInDB
from any_auth.utils.auth import generate_password, verify_password
from any_auth.utils.jwt_tokens import convert_oauth2_token_to_jwt
from any_auth.utils.oauth2 import generate_refresh_token, generate_token

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.post("/token", response_model=TokenResponse, deprecated=True)
async def api_token(
    auth_token_request: AuthTokenRequest = fastapi.Body(...),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    allowed_active_user_roles: typing.Tuple[
        UserInDB, typing.List[Role]
    ] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_platform(
            Permission.USER_CREATE,
        )
    ),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
) -> TokenResponse:
    might_user_in_db = await asyncio.to_thread(
        backend_client.users.retrieve_by_email, auth_token_request.email
    )

    # Create new user if they don't exist
    if might_user_in_db is None:
        logger.debug(f"Creating new user: {auth_token_request.email}")
        username = auth_token_request.email.split("@")[0] + "_" + str(uuid.uuid4())[:8]
        user_create = UserCreate(
            username=username,
            full_name=auth_token_request.name,
            email=auth_token_request.email,
            password=generate_password(32),
            picture=auth_token_request.picture,
            metadata={"provider": auth_token_request.provider},
        )
        user_in_db = backend_client.users.create(user_create)
        logger.debug(f"New user created: {user_in_db.id}")
    else:
        user_in_db = might_user_in_db

    # Create OAuth2Token
    now = int(time.time())
    oauth2_token = OAuth2Token(
        user_id=user_in_db.id,
        client_id="auth_token_client",  # Using a standard client ID for this flow
        scope="openid email profile",
        expires_at=now + settings.TOKEN_EXPIRATION_TIME,
        access_token=generate_token(),
        refresh_token=generate_refresh_token(),
    )

    # Convert to JWT format
    oauth2_token = convert_oauth2_token_to_jwt(oauth2_token, settings)

    # Store token in database
    await asyncio.to_thread(backend_client.oauth2_tokens.create, oauth2_token)

    # Return standardized TokenResponse
    return TokenResponse(
        access_token=oauth2_token.access_token,
        token_type=oauth2_token.token_type,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        refresh_token=oauth2_token.refresh_token,
        scope=oauth2_token.scope,
    )


@router.post("/login", response_model=TokenResponse, deprecated=True)
async def api_login(
    request: fastapi.Request,
    form_data: typing.Annotated[OAuth2PasswordRequestForm, fastapi.Depends()],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> TokenResponse:
    # This endpoint already uses OAuth2Token, so no changes needed
    if not form_data.username or not form_data.password:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password",
        )

    is_email = IS.is_email(form_data.username)
    if is_email:
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_email, form_data.username
        )
    else:
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_username, form_data.username
        )

    if not user_in_db:
        logger.warning(f"User not found: {form_data.username}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Invalid username/email or password",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user_in_db.hashed_password):
        logger.warning(f"Invalid password for user: {user_in_db.id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "Invalid username/email or password",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_in_db.disabled:
        logger.warning(f"Login attempt for disabled user: {user_in_db.id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": OAuth2Error.INVALID_GRANT,
                "error_description": "User account is disabled",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = int(time.time())
    oauth2_token = OAuth2Token(
        user_id=user_in_db.id,
        client_id="ropc_login_client",
        scope="openid email profile",
        expires_at=now + settings.TOKEN_EXPIRATION_TIME,
        access_token=generate_token(),
        refresh_token=generate_refresh_token(),
        token_type=TokenType.BEARER,
    )

    # Convert to JWT format
    oauth2_token = convert_oauth2_token_to_jwt(oauth2_token, settings)

    try:
        await asyncio.to_thread(backend_client.oauth2_tokens.create, oauth2_token)
        logger.info(f"Stored OAuth2 token {oauth2_token.id} for user {user_in_db.id}")
    except Exception as e:
        logger.exception(f"Failed to store OAuth2 token: {e}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate token.",
        )

    return TokenResponse(
        access_token=oauth2_token.access_token,
        token_type=oauth2_token.token_type,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        refresh_token=oauth2_token.refresh_token,
        scope=oauth2_token.scope,
    )


@router.post("/logout", deprecated=True)
async def api_logout(
    request: fastapi.Request,
    token: str = fastapi.Depends(oauth2_scheme),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    # Blacklist token
    cache.set(
        f"token_blacklist:{token}",
        True,
        settings.TOKEN_EXPIRATION_TIME + 1,
    )

    # Also revoke token in database if it exists
    try:
        await asyncio.to_thread(
            backend_client.oauth2_tokens.revoke_token, token, "access_token"
        )
    except Exception as e:
        # Log but don't fail if token revocation fails
        logger.warning(f"Error revoking token in database: {e}")

    return fastapi.responses.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/refresh", response_model=TokenResponse, deprecated=True)
async def api_refresh_token(
    grant_type: str = fastapi.Form(...),
    refresh_token: str = fastapi.Form(...),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> TokenResponse:
    # Ensure the grant type is "refresh_token"
    if grant_type != "refresh_token":
        logger.warning(f"Invalid grant type: {grant_type}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Invalid grant type. Must be 'refresh_token'.",
        )

    # Retrieve the token from the database
    token = await asyncio.to_thread(
        backend_client.oauth2_tokens.retrieve_by_refresh_token, refresh_token
    )

    if not token:
        logger.warning(f"Refresh token not found: {refresh_token[:10]}...")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    if token.revoked:
        logger.warning(f"Refresh token revoked: {refresh_token[:10]}...")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked.",
        )

    if token.is_expired():
        logger.warning(f"Refresh token expired: {refresh_token[:10]}...")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )

    # Generate a new token
    now = int(time.time())
    new_token = OAuth2Token(
        user_id=token.user_id,
        client_id=token.client_id,
        scope=token.scope,
        expires_at=now + settings.TOKEN_EXPIRATION_TIME,
        access_token=generate_token(),
        refresh_token=generate_refresh_token(),  # Generate new refresh token
        token_type=token.token_type,
    )

    # Convert to JWT format
    new_token = convert_oauth2_token_to_jwt(new_token, settings)

    # Store the new token
    await asyncio.to_thread(backend_client.oauth2_tokens.create, new_token)

    # Revoke the old refresh token
    await asyncio.to_thread(backend_client.oauth2_tokens.revoke_token, refresh_token)

    # Return a standard TokenResponse
    return TokenResponse(
        access_token=new_token.access_token,
        token_type=new_token.token_type,
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        refresh_token=new_token.refresh_token,
        scope=new_token.scope,
    )
