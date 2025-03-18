import asyncio
import datetime
import logging
import time
import typing
import uuid
import zoneinfo

import diskcache
import fastapi
import redis
from fastapi.security import OAuth2PasswordRequestForm

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
import any_auth.utils.is_ as IS
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.deps.auth import depends_active_user, oauth2_scheme
from any_auth.types.auth import AuthTokenRequest
from any_auth.types.role import Permission, Role
from any_auth.types.token_ import Token
from any_auth.types.user import UserCreate, UserInDB
from any_auth.utils.auth import generate_password, verify_password

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.post("/token")
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
) -> Token:
    might_user_in_db = await asyncio.to_thread(
        backend_client.users.retrieve_by_email, auth_token_request.email
    )

    # Create new user if they don't exist
    if might_user_in_db is None:
        logger.debug(f"Creating new user: {auth_token_request.email}")
        _username = (
            auth_token_request.email.split("@")[0]
            + "_"
            + str(uuid.uuid4()).replace("-", "")[:16]
        )
        _user_create_data = dict(
            username=_username,
            full_name=auth_token_request.name,
            email=auth_token_request.email,
            password=generate_password(32),
            picture=auth_token_request.picture,
            metadata={"provider": auth_token_request.provider},
        )
        user_in_db = backend_client.users.create(
            UserCreate.model_validate(_user_create_data)
        )
        logger.debug(
            f"New user created: {user_in_db.id} for {auth_token_request.email}"
        )
    else:
        user_in_db = might_user_in_db

    # Build a Token object
    now_ts = int(time.time())
    token = Token(
        access_token=JWTManager.create_jwt_token(
            user_id=user_in_db.id,
            expires_in=settings.TOKEN_EXPIRATION_TIME,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
            now=now_ts,
        ),
        refresh_token=JWTManager.create_jwt_token(
            user_id=user_in_db.id,
            expires_in=settings.REFRESH_TOKEN_EXPIRATION_TIME,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
            now=now_ts,
        ),
        token_type="Bearer",
        scope="openid email profile",
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        expires_at=now_ts + settings.TOKEN_EXPIRATION_TIME,
        issued_at=datetime.datetime.fromtimestamp(
            now_ts, zoneinfo.ZoneInfo("UTC")
        ).isoformat(),
    )

    return token


@router.post("/login")
async def api_login(
    form_data: typing.Annotated[OAuth2PasswordRequestForm, fastapi.Depends()],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    use_cache: bool = fastapi.Query(default=True),
) -> Token:
    if not form_data.username or not form_data.password:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password",
        )

    is_email = IS.is_email(form_data.username)
    if is_email:
        logger.debug(f"Trying to retrieve user by email: {form_data.username}")
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_email, form_data.username
        )
    else:
        logger.debug(f"Trying to retrieve user by username: {form_data.username}")
        user_in_db = await asyncio.to_thread(
            backend_client.users.retrieve_by_username, form_data.username
        )

    if not user_in_db:
        logger.warning(f"User not found for '{form_data.username}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )
    else:
        if is_email:
            logger.debug(f"User retrieved by email: '{user_in_db.id}'")
        else:
            logger.debug(f"User retrieved by username: '{user_in_db.id}'")

    if not verify_password(form_data.password, user_in_db.hashed_password):
        logger.warning(f"Invalid password for user: '{user_in_db.id}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )
    else:
        logger.debug(f"Password verified for user: '{user_in_db.id}'")

    # Check if the user is already logged in
    if use_cache:
        might_cached_token = cache.get(f"token:{user_in_db.id}")
        if might_cached_token:
            logger.debug(f"User '{user_in_db.id}' is already logged in")
            cached_token = Token.model_validate_json(might_cached_token)  # type: ignore
            if cached_token.expires_at > int(time.time()):
                return cached_token
            else:
                logger.debug(
                    f"User '{user_in_db.id}' cached token expired, generating new one"
                )

    # Build a Token object
    now_ts = int(time.time())
    token = Token(
        access_token=JWTManager.create_jwt_token(
            user_id=user_in_db.id,
            expires_in=settings.TOKEN_EXPIRATION_TIME,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
            now=now_ts,
        ),
        refresh_token=JWTManager.create_jwt_token(
            user_id=user_in_db.id,
            expires_in=settings.REFRESH_TOKEN_EXPIRATION_TIME,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
            now=now_ts,
        ),
        token_type="Bearer",
        scope="openid email profile",
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        expires_at=now_ts + settings.TOKEN_EXPIRATION_TIME,
        issued_at=datetime.datetime.fromtimestamp(
            now_ts, zoneinfo.ZoneInfo("UTC")
        ).isoformat(),
    )

    # Cache the token
    if use_cache:
        cache.set(
            f"token:{user_in_db.id}",
            token.model_dump_json(),
            settings.TOKEN_EXPIRATION_TIME + 1,
        )

    return token


@router.post("/logout")
async def api_logout(
    request: fastapi.Request,
    token: Token = fastapi.Depends(oauth2_scheme),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
):
    might_cached_token = cache.get(f"token:{active_user.id}")
    if might_cached_token:
        old_token = Token.model_validate_json(might_cached_token)  # type: ignore
        cache.delete(f"token:{active_user.id}")
        cache.set(
            f"token_blacklist:{old_token.access_token}",
            True,
            settings.TOKEN_EXPIRATION_TIME + 1,
        )
        cache.set(
            f"token_blacklist:{old_token.refresh_token}",
            True,
            settings.TOKEN_EXPIRATION_TIME + 1,
        )

    cache.set(
        f"token_blacklist:{token}",
        True,
        settings.TOKEN_EXPIRATION_TIME + 1,
    )
    return fastapi.responses.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post("/refresh")
async def api_refresh_token(
    grant_type: str = fastapi.Form(...),
    refresh_token: str = fastapi.Form(...),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
) -> Token:
    # Ensure the grant type is "refresh_token"
    if grant_type != "refresh_token":
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Invalid grant type. Must be 'refresh_token'.",
        )

    # Check if this refresh token is already blacklisted
    if cache.get(f"token_blacklist:{refresh_token}"):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        )

    # Verify and decode the refresh token.
    try:
        payload = JWTManager.verify_jwt_token(
            refresh_token,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
        )

        user_id = payload.get("sub") or payload.get("user_id")

        if not user_id:
            raise ValueError("Missing user_id in token payload")

    except Exception as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from e

    # Blacklist the old refresh token so it can’t be used again
    old_token_json = cache.get(f"token:{user_id}")
    if old_token_json:
        old_token = Token.model_validate_json(old_token_json)  # type: ignore
        cache.delete(f"token:{user_id}")
        cache.set(
            f"token_blacklist:{old_token.access_token}",
            True,
            settings.REFRESH_TOKEN_EXPIRATION_TIME + 1,
        )
        cache.set(
            f"token_blacklist:{old_token.refresh_token}",
            True,
            settings.REFRESH_TOKEN_EXPIRATION_TIME + 1,
        )
    cache.set(
        f"token_blacklist:{refresh_token}",
        True,
        settings.REFRESH_TOKEN_EXPIRATION_TIME + 1,
    )

    # Generate new tokens
    # Build and return the Token response
    now_ts = int(time.time())
    token = Token(
        access_token=JWTManager.create_jwt_token(
            user_id=user_id,
            expires_in=settings.TOKEN_EXPIRATION_TIME,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
            now=now_ts,
        ),
        refresh_token=JWTManager.create_jwt_token(
            user_id=user_id,
            expires_in=settings.REFRESH_TOKEN_EXPIRATION_TIME,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
            now=now_ts,
        ),
        token_type="Bearer",
        scope="openid email profile",
        expires_in=settings.TOKEN_EXPIRATION_TIME,
        expires_at=now_ts + settings.TOKEN_EXPIRATION_TIME,
        issued_at=datetime.datetime.fromtimestamp(
            now_ts, zoneinfo.ZoneInfo("UTC")
        ).isoformat(),
    )
    return token
