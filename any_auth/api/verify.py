import asyncio
import logging
import time
import typing

import diskcache
import fastapi
import jwt
import pydantic
import redis

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
import any_auth.utils.auth
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.deps.auth import oauth2_scheme
from any_auth.types.api_key import APIKeyInDB
from any_auth.types.role import Role
from any_auth.types.role_assignment import PLATFORM_ID, RoleAssignment
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


class VerifyRequest(pydantic.BaseModel):
    resource_id: typing.Text = pydantic.Field(
        ..., description="The ID of the resource to verify"
    )
    permissions: typing.Text = pydantic.Field(
        ..., description="Comma-separated list of permissions"
    )

    @property
    def required_permissions(self) -> typing.List[typing.Text]:
        return [perm.strip() for perm in self.permissions.split(",") if perm.strip()]


class VerifyResponse(pydantic.BaseModel):
    success: bool
    detail: typing.Text | None = None


@router.post("/verify")
async def api_verify(
    token: typing.Annotated[typing.Text, fastapi.Depends(oauth2_scheme)],
    verify_request: VerifyRequest = fastapi.Body(...),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
):
    user_or_api_key: typing.Union[UserInDB, APIKeyInDB] | None = None

    # Check if token is blacklisted
    if await asyncio.to_thread(cache.get, f"token_blacklist:{token}"):  # type: ignore
        logger.debug(f"Token blacklisted: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token blacklisted",
        )

    try:
        payload = JWTManager.verify_jwt_token(
            token,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(f"Entered JWT token: '{token[:6]}...{token[-6:]}'")

        if time.time() > payload["exp"]:
            raise jwt.ExpiredSignatureError

        might_user_id = JWTManager.get_user_id_from_payload(dict(payload))

        if not might_user_id:
            logger.error(f"No user ID found in token: '{token[:6]}...{token[-6:]}'")
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user_id = might_user_id

        might_user = await asyncio.to_thread(backend_client.users.retrieve, user_id)

        if not might_user:
            logger.error(f"User from token not found: {user_id}")
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        user_or_api_key = might_user

    except jwt.ExpiredSignatureError:
        logger.debug(f"Token expired: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    except jwt.InvalidTokenError:
        logger.debug(f"Token is not a JWT token: '{token[:6]}...{token[-6:]}'")

        might_api_key = backend_client.api_keys.retrieve_by_plain_key(token)

        if might_api_key is None:
            logger.debug(f"Invalid token: '{token[:6]}...{token[-6:]}'")
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        logger.debug(f"Entered API key: '{token[:6]}...{token[-6:]}'")
        user_or_api_key = might_api_key

    if user_or_api_key is None:
        logger.error(f"User or API key not found: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    roles_assignments: typing.List[RoleAssignment] = []
    for _rs in await asyncio.gather(
        asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_target_id,
            target_id=user_or_api_key.id,
            resource_id=PLATFORM_ID,
        ),
        asyncio.to_thread(
            backend_client.role_assignments.retrieve_by_target_id,
            target_id=user_or_api_key.id,
            resource_id=verify_request.resource_id,
        ),
    ):
        roles_assignments.extend(_rs)

    roles: typing.List[Role] = []
    if len(roles_assignments) == 0:
        logger.debug(f"No roles assignments found for target: {user_or_api_key.id}")
    else:
        role_map: typing.Dict[typing.Text, Role] = {}
        for _rs in roles_assignments:
            if _rs.role_id in role_map:
                continue

            _tar_role, _roles = await asyncio.gather(
                asyncio.to_thread(backend_client.roles.retrieve, _rs.role_id),
                asyncio.to_thread(
                    backend_client.roles.retrieve_all_child_roles, id=_rs.role_id
                ),
            )
            if _tar_role is not None:
                role_map[_tar_role.id] = _tar_role
            for _r in _roles:
                role_map[_r.id] = _r

        roles.extend(list(role_map.values()))

    user_or_api_key_perms = {perm for role in roles for perm in role.permissions}

    any_auth.utils.auth.raise_if_not_enough_permissions(
        verify_request.required_permissions,
        user_or_api_key_perms,
        debug_active_user=user_or_api_key,
        debug_user_roles=roles,
        debug_resource_id=verify_request.resource_id,
    )

    return VerifyResponse(success=True)
