import asyncio
import logging
import typing

import diskcache
import fastapi
import jwt
import redis
from fastapi.security import OAuth2PasswordBearer

import any_auth.deps.app_state as AppState
import any_auth.utils.auth
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.api_key import APIKeyInDB
from any_auth.types.organization import Organization
from any_auth.types.organization_member import OrganizationMember
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import PLATFORM_ID, RoleAssignment
from any_auth.types.user import UserInDB
from any_auth.utils.jwt_tokens import verify_jwt_access_token

logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def allowed_token(
    token: typing.Annotated[typing.Text, fastapi.Depends(oauth2_scheme)],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
) -> typing.Text:
    # Check if token is blacklisted
    if await asyncio.to_thread(cache.get, f"token_blacklist:{token}"):  # type: ignore
        logger.debug(f"Token blacklisted: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    return token


async def depends_user_id(
    token: typing.Annotated[typing.Text, fastapi.Depends(allowed_token)],
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.Text | None:
    user_id: typing.Text | None = None

    # First try to validate as JWT token
    try:
        # Check if token appears to be a JWT (contains two dots)
        if token.count(".") == 2:
            # Verify JWT signature and get payload
            claims = verify_jwt_access_token(token, settings)
            user_id = claims.get("sub")

            if not user_id:
                logger.warning("JWT token missing 'sub' claim")
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format",
                )
        else:
            # Not a JWT token, try database lookup
            raise jwt.InvalidTokenError("Not a JWT token")

    except jwt.ExpiredSignatureError:
        logger.debug(f"JWT token expired: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        # Not a JWT or JWT validation failed, try database lookup
        logger.debug(
            "JWT validation failed, trying database lookup: "
            + f"'{token[:6]}...{token[-6:]}'"
        )

        # Look up token in database
        oauth2_token = await asyncio.to_thread(
            backend_client.oauth2_tokens.retrieve_by_access_token, token
        )

        if not oauth2_token:
            logger.debug(f"Token not found in database: '{token[:6]}...{token[-6:]}'")
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Check if token is revoked
        if oauth2_token.revoked:
            logger.debug(f"Token revoked: '{token[:6]}...{token[-6:]}'")
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        # Check if token is expired
        if oauth2_token.is_expired():
            logger.debug(f"Token expired: '{token[:6]}...{token[-6:]}'")
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        user_id = oauth2_token.user_id

    except Exception as e:
        logger.exception(e)
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate token",
        )

    return user_id


async def depends_current_user(
    token: typing.Annotated[typing.Text, fastapi.Depends(oauth2_scheme)],
    user_id: typing.Text | None = fastapi.Depends(depends_user_id),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> UserInDB:
    """
    Dependency that validates the access token and returns the current user.
    Supports both JWT tokens and database-stored OAuth2Tokens.
    """

    # Retrieve and validate user
    if not user_id:
        logger.warning(f"No user ID found in token: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_in_db = await asyncio.to_thread(backend_client.users.retrieve, user_id)

    if not user_in_db:
        logger.warning(f"User not found: {user_id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user_in_db


async def deps_api_key(
    token: typing.Annotated[typing.Text, fastapi.Depends(oauth2_scheme)],
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    might_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve_by_plain_key, token
    )

    if might_api_key is None:
        logger.debug(f"Invalid token: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    logger.debug(f"Entered API key: '{token[:6]}...{token[-6:]}'")
    api_key = might_api_key

    if api_key is None:
        logger.error(f"User or API key not found: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return api_key


async def depends_active_user(
    user: UserInDB = fastapi.Depends(depends_current_user),
) -> UserInDB:
    """
    Dependency that ensures the current user is active (not disabled).
    """
    if user.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    return user


async def deps_active_user_or_api_key(
    token: typing.Annotated[typing.Text, fastapi.Depends(allowed_token)],
    user_id: typing.Text | None = fastapi.Depends(depends_user_id),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.Union[UserInDB, APIKeyInDB]:
    if user_id is not None:
        # Should be user
        user = await asyncio.to_thread(backend_client.users.retrieve, user_id)

        if user is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Check if user is disabled
        if user.disabled:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        return user
    else:
        # Should be API key
        api_key = await asyncio.to_thread(
            backend_client.api_keys.retrieve_by_plain_key, token
        )

        if api_key:
            return api_key

        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# === Platform ===
async def depends_active_user_role_assignments_in_platform(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[RoleAssignment]:
    return await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=active_user.id,
        resource_id=PLATFORM_ID,
    )


async def depends_active_user_roles_in_platform(
    role_assignments: typing.List[RoleAssignment] = fastapi.Depends(
        depends_active_user_role_assignments_in_platform
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[Role]:
    if len(role_assignments) == 0:
        return []

    return await asyncio.to_thread(
        backend_client.roles.retrieve_by_ids,
        [assignment.role_id for assignment in role_assignments],
    )


# === End of Platform ===


# === Organization ===
async def depends_organization(
    organization_id: typing.Text = fastapi.Path(
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


async def depends_active_user_roles_assignments_in_organization(
    organization: Organization = fastapi.Depends(depends_active_organization),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[RoleAssignment]:
    # Organization roles
    organization_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=active_user.id,
        resource_id=organization.id,
    )

    return organization_role_assignments


async def depends_active_user_roles_in_organization(
    roles_assignments: typing.List[RoleAssignment] = fastapi.Depends(
        depends_active_user_roles_assignments_in_organization
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[Role]:
    if len(roles_assignments) == 0:
        return []

    _roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_ids,
        [assignment.role_id for assignment in roles_assignments],
    )

    role_map: typing.Dict[typing.Text, Role] = {_r.id: _r for _r in _roles}
    for _r in _roles:
        _roles = await asyncio.to_thread(
            backend_client.roles.retrieve_all_child_roles,
            id=_r.id,
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


async def depends_raise_if_not_platform_and_not_organization_member(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_role_assignments_platform: typing.List[RoleAssignment] = fastapi.Depends(
        depends_active_user_role_assignments_in_platform
    ),
    organization_member: OrganizationMember | None = fastapi.Depends(
        depends_organization_member
    ),
) -> OrganizationMember | None:
    # Check if user has platform roles
    if len(active_role_assignments_platform) > 0:
        logger.debug(
            f"User '{active_user.username}' ({active_user.id}) "
            + "has platform role assignments: "
            + f"{', '.join([ra.role_id for ra in active_role_assignments_platform])}. "  # noqa: E501
            + "Skipping organization member check",
        )
        return organization_member

    # Check if user is organization member
    if organization_member:
        logger.debug(
            f"User '{active_user.username}' ({active_user.id}) "
            + f"is an organization ({organization_member.organization_id}) "
            + f"member ({organization_member.id}). "
        )
        return organization_member

    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_403_FORBIDDEN,
        detail="User is not allowed to access this organization",
    )


# === End of Organization ===


# === Project ===
async def depends_project(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    might_project = await asyncio.to_thread(
        backend_client.projects.retrieve, project_id
    )

    if not might_project:
        logger.warning(f"Project ID not found: {project_id}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return might_project


async def depends_active_project(
    project: Project = fastapi.Depends(depends_project),
) -> Project:
    if project.disabled:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Project is disabled",
        )

    return project


async def depends_active_user_roles_assignments_in_project(
    project: Project = fastapi.Depends(depends_active_project),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[RoleAssignment]:
    # Project roles
    project_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=active_user.id,
        resource_id=project.id,
    )

    return project_role_assignments


async def depends_active_user_roles_in_project(
    roles_assignments: typing.List[RoleAssignment] = fastapi.Depends(
        depends_active_user_roles_assignments_in_project
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[Role]:
    if len(roles_assignments) == 0:
        return []

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

    return list(role_map.values())


async def depends_project_member(
    project: Project = fastapi.Depends(depends_active_project),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> ProjectMember | None:
    project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_project_user_id,
        project.id,
        active_user.id,
    )

    return project_member


async def depends_raise_if_not_platform_and_not_project_member(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_role_assignments_platform: typing.List[RoleAssignment] = fastapi.Depends(
        depends_active_user_role_assignments_in_platform
    ),
    project_member: ProjectMember | None = fastapi.Depends(depends_project_member),
) -> ProjectMember | None:
    # Check if user has platform roles
    if len(active_role_assignments_platform) > 0:
        logger.debug(
            f"User '{active_user.username}' ({active_user.id}) "
            + "has platform role assignments: "
            + f"{', '.join([ra.role_id for ra in active_role_assignments_platform])}. "  # noqa: E501
            + "Skipping project member check",
        )
        return project_member

    # Check if user is project member
    if project_member:
        logger.debug(
            f"User '{active_user.username}' ({active_user.id}) "
            + f"is a project ('{project_member.project_id}') member "
            + f"({project_member.id}). "
        )
        return project_member

    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_403_FORBIDDEN,
        detail="User is not allowed to access this project",
    )


# === End of Project ===


# === Permissions ===
def depends_permissions_for_platform(
    *required_permissions: Permission,
) -> typing.Callable[
    ...,
    typing.Coroutine[
        None,
        None,
        typing.Tuple[UserInDB, typing.List[Role], typing.List[RoleAssignment]],
    ],
]:
    async def _dependency(
        active_user: UserInDB = fastapi.Depends(depends_active_user),
        active_role_assignments_platform: typing.List[RoleAssignment] = fastapi.Depends(
            depends_active_user_role_assignments_in_platform
        ),
        active_roles_platform: typing.List[Role] = fastapi.Depends(
            depends_active_user_roles_in_platform
        ),
        backend_client: BackendClient = fastapi.Depends(
            AppState.depends_backend_client
        ),
    ) -> typing.Tuple[UserInDB, typing.List[Role], typing.List[RoleAssignment]]:
        if len(active_role_assignments_platform) == 0:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_403_FORBIDDEN,
                detail="User does not have any platform roles",
            )

        user_perms = {
            perm for role in active_roles_platform for perm in role.permissions
        }

        any_auth.utils.auth.raise_if_not_enough_permissions(
            required_permissions,
            user_perms,
            debug_active_user=active_user,
            debug_user_roles=active_roles_platform,
            debug_resource_id=PLATFORM_ID,
            debug_resource_type="platform",
        )

        return (active_user, active_roles_platform, active_role_assignments_platform)

    return _dependency


def depends_permissions_for_organization(
    *required_permissions: Permission,
) -> typing.Callable[
    ...,
    typing.Coroutine[
        None,
        None,
        typing.Tuple[
            UserInDB,
            typing.List[Role],
            typing.List[RoleAssignment],
            OrganizationMember | None,
            Organization,
        ],
    ],
]:
    async def _dependency(
        active_user: UserInDB = fastapi.Depends(depends_active_user),
        organization: Organization = fastapi.Depends(depends_active_organization),
        active_role_assignments_platform: typing.List[RoleAssignment] = fastapi.Depends(
            depends_active_user_role_assignments_in_platform
        ),
        active_roles_platform: typing.List[Role] = fastapi.Depends(
            depends_active_user_roles_in_platform
        ),
        active_role_assignments_organization: typing.List[
            RoleAssignment
        ] = fastapi.Depends(depends_active_user_roles_assignments_in_organization),
        active_roles_organization: typing.List[Role] = fastapi.Depends(
            depends_active_user_roles_in_organization
        ),
        organization_member: OrganizationMember | None = fastapi.Depends(
            depends_raise_if_not_platform_and_not_organization_member
        ),
    ) -> typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        OrganizationMember | None,
        Organization,
    ]:
        roles = active_roles_organization + active_roles_platform
        rs = active_role_assignments_organization + active_role_assignments_platform

        user_perms = {perm for role in roles for perm in role.permissions}

        any_auth.utils.auth.raise_if_not_enough_permissions(
            required_permissions,
            user_perms,
            debug_active_user=active_user,
            debug_user_roles=roles,
            debug_resource_id=organization.id,
            debug_resource_type="organization",
        )

        return (active_user, roles, rs, organization_member, organization)

    return _dependency


def depends_permissions_for_project(
    *required_permissions: Permission,
) -> typing.Callable[
    ...,
    typing.Coroutine[
        None,
        None,
        typing.Tuple[
            UserInDB,
            typing.List[Role],
            typing.List[RoleAssignment],
            ProjectMember | None,
            Project,
        ],
    ],
]:
    async def _dependency(
        active_user: UserInDB = fastapi.Depends(depends_active_user),
        project: Project = fastapi.Depends(depends_active_project),
        active_role_assignments_platform: typing.List[RoleAssignment] = fastapi.Depends(
            depends_active_user_role_assignments_in_platform
        ),
        active_role_assignments_project: typing.List[RoleAssignment] = fastapi.Depends(
            depends_active_user_roles_assignments_in_project
        ),
        active_roles_platform: typing.List[Role] = fastapi.Depends(
            depends_active_user_roles_in_platform
        ),
        active_roles_project: typing.List[Role] = fastapi.Depends(
            depends_active_user_roles_in_project
        ),
        project_member: ProjectMember | None = fastapi.Depends(
            depends_raise_if_not_platform_and_not_project_member
        ),
    ) -> typing.Tuple[
        UserInDB,
        typing.List[Role],
        typing.List[RoleAssignment],
        ProjectMember | None,
        Project,
    ]:
        roles = active_roles_project + active_roles_platform
        rs = active_role_assignments_project + active_role_assignments_platform

        user_perms = {perm for role in roles for perm in role.permissions}

        any_auth.utils.auth.raise_if_not_enough_permissions(
            required_permissions,
            user_perms,
            debug_active_user=active_user,
            debug_user_roles=roles,
            debug_resource_id=project.id,
            debug_resource_type="project",
        )

        return (active_user, roles, rs, project_member, project)

    return _dependency


# === End of Permissions ===


# === OAuth2 ===
async def validate_oauth2_token(
    token: typing.Annotated[str, fastapi.Depends(oauth2_scheme)],
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    settings: Settings = fastapi.Depends(AppState.depends_settings),
    cache: diskcache.Cache | redis.Redis = fastapi.Depends(AppState.depends_cache),
) -> dict:
    """
    Validate an OAuth2 JWT token and return its claims.

    This dependency can be used to protect API endpoints by requiring a valid OAuth2 token
    with specific scopes.
    """  # noqa: E501
    # Check if token is blacklisted
    if cache.get(f"token_blacklist:{token}"):
        logger.debug(f"Token blacklisted: '{token[:6]}...{token[-6:]}'")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    try:
        # Parse token claims without validating signature first
        unverified_claims = jwt.decode(token, options={"verify_signature": False})

        # Check for token ID (jti) to see if it's a JWT token we issued
        jti = unverified_claims.get("jti")
        if jti:
            # Try to verify as JWT
            try:
                claims = verify_jwt_access_token(token, settings)
                return claims
            except jwt.InvalidTokenError as e:
                logger.debug(f"JWT validation failed: {str(e)}")
                # Fall through to legacy token check

        # Legacy token check
        oauth2_token = await asyncio.to_thread(
            backend_client.oauth2_tokens.retrieve_by_access_token, token
        )

        if not oauth2_token:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        if oauth2_token.revoked:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        if oauth2_token.is_expired():
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        # Return claims in same format as JWT for consistency
        return {
            "sub": oauth2_token.user_id,
            "client_id": oauth2_token.client_id,
            "scope": oauth2_token.scope,
            "exp": oauth2_token.expires_at,
            "iat": oauth2_token.issued_at,
            "jti": oauth2_token.id,
        }

    except (jwt.InvalidTokenError, Exception) as e:
        logger.debug(f"Token validation failed: {str(e)}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def requires_scope(*required_scopes: str):
    """
    Dependency factory that checks if the token has the required OAuth2 scopes.

    Usage:
        @app.get("/api/resource")
        async def get_resource(
            claims: dict = fastapi.Depends(validate_oauth2_token),
            has_scope: bool = fastapi.Depends(requires_scope("read:resource"))
        ):
            return {"data": "protected resource"}
    """

    async def check_scope(
        claims: dict = fastapi.Depends(validate_oauth2_token),
    ) -> bool:
        token_scopes = claims.get("scope", "").split()

        # Check if token has all required scopes
        missing_scopes = [
            scope for scope in required_scopes if scope not in token_scopes
        ]

        if missing_scopes:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient scope. Missing: {', '.join(missing_scopes)}",
                headers={
                    "WWW-Authenticate": f'Bearer scope="{" ".join(required_scopes)}"'
                },
            )

        return True

    return check_scope


# === End of OAuth2 ===
