import asyncio
import logging
import time
import typing

import diskcache
import fastapi
import jwt
import redis
from fastapi.security import OAuth2PasswordBearer

import any_auth.deps.app_state as AppState
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.organization import Organization
from any_auth.types.organization_member import OrganizationMember
from any_auth.types.role import Role
from any_auth.types.role_assignment import (
    PLATFORM_ID,
    RoleAssignment,
    RoleAssignmentListAdapter,
)
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def depends_current_user(
    token: typing.Annotated[typing.Text, fastapi.Depends(oauth2_scheme)],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
) -> UserInDB:
    try:
        payload = JWTManager.verify_jwt_token(
            token,
            jwt_secret=settings.JWT_SECRET_KEY.get_secret_value(),
            jwt_algorithm=settings.JWT_ALGORITHM,
        )

        if time.time() > payload["exp"]:
            raise jwt.ExpiredSignatureError

    except jwt.ExpiredSignatureError:
        logger.debug(f"Token expired: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        logger.debug(f"Invalid token: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        logger.exception(e)
        logger.error("Error during session active user")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    user_id = JWTManager.get_user_id_from_payload(payload)

    if not user_id:
        logger.debug(f"No user ID found in token: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Check if token is blacklisted
    if cache.get(f"token_blacklist:{token}"):
        logger.debug(f"Token blacklisted: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token blacklisted",
        )

    user_in_db = backend_client.users.retrieve(user_id)

    if not user_in_db:
        logger.error(f"User from token not found: {user_id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user_in_db


async def depends_active_user(
    user: UserInDB = fastapi.Depends(depends_current_user),
) -> UserInDB:
    if user.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
        )
    return user


async def depends_organization(
    organization_id: typing.Text = fastapi.Query(
        ..., description="The ID of the organization to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Organization:
    organization_id = organization_id.strip()
    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    might_org = await asyncio.to_thread(
        backend_client.organizations.retrieve, organization_id
    )

    if not might_org:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return might_org


async def depends_active_organization(
    organization: Organization = fastapi.Depends(depends_organization),
) -> Organization:
    if organization.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Organization is disabled",
        )
    return organization


async def depends_roles_assignments_for_user_in_organization(
    organization: Organization = fastapi.Depends(depends_active_organization),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[RoleAssignment]:
    # Organization roles
    organization_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        active_user.id,
        resource_id=organization.id,
    )

    # Platform roles
    platform_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        active_user.id,
        resource_id=PLATFORM_ID,
    )

    return organization_role_assignments + platform_role_assignments


async def depends_roles_for_user_in_organization(
    roles_assignments: typing.List[RoleAssignment] = fastapi.Depends(
        depends_roles_assignments_for_user_in_organization
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[Role]:
    role_map: typing.Dict[typing.Text, Role] = {}
    for _rs in roles_assignments:
        if _rs.role_id in role_map:
            continue
        _roles = await asyncio.to_thread(
            backend_client.roles.retrieve_all_child_roles,
            id=_rs.role_id,
        )
        for _r in _roles:
            role_map[_r.id] = _r

    return list(role_map.values())


async def depends_organization_member(
    organization: Organization = fastapi.Depends(depends_active_organization),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> OrganizationMember | None:
    org_member = await asyncio.to_thread(
        backend_client.organization_members.retrieve_by_organization_user_id,
        organization.id,
        active_user.id,
    )

    return org_member


async def depends_raise_if_not_user_allowed_to_access_organization(
    organization: Organization = fastapi.Depends(depends_active_organization),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_role_assignments: typing.List[RoleAssignment] = fastapi.Depends(
        depends_roles_assignments_for_user_in_organization
    ),
    active_roles: typing.List[Role] = fastapi.Depends(
        depends_roles_for_user_in_organization
    ),
    organization_member: OrganizationMember | None = fastapi.Depends(
        depends_organization_member
    ),
) -> None:
    # Check if user has platform roles
    platform_role_assignments = [
        _rs for _rs in active_role_assignments if _rs.resource_id == PLATFORM_ID
    ]
    if len(platform_role_assignments) > 0:
        logger.info(
            f"User ({active_user.model_dump_json()}) "
            + "has platform role assignments: "
            + f"{RoleAssignmentListAdapter.dump_json(platform_role_assignments)}. "
            + "Skipping organization member check",
        )
        return

    # Check if user is organization member
    if organization_member:
        logger.info(
            f"User ({active_user.model_dump_json()}) "
            + "is an organization member: "
            + f"{organization_member.model_dump_json()}. "
        )
        return

    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_403_FORBIDDEN,
        detail="User is not allowed to access this organization",
    )
