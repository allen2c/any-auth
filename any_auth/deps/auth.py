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
import any_auth.utils.auth
import any_auth.utils.jwt_manager as JWTManager
from any_auth.backend import BackendClient
from any_auth.config import Settings
from any_auth.types.organization import Organization
from any_auth.types.organization_member import OrganizationMember
from any_auth.types.project import Project
from any_auth.types.project_member import ProjectMember
from any_auth.types.role import Permission, Role
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


# === Platform ===
async def depends_active_user_role_assignments_in_platform(
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> typing.List[RoleAssignment]:
    return await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_user_id,
        active_user.id,
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
        backend_client.role_assignments.retrieve_by_user_id,
        active_user.id,
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
            f"User ({active_user.model_dump_json()}) "
            + "has platform role assignments: "
            + f"{RoleAssignmentListAdapter.dump_json(active_role_assignments_platform)}. "  # noqa: E501
            + "Skipping organization member check",
        )
        return organization_member

    # Check if user is organization member
    if organization_member:
        logger.debug(
            f"User ({active_user.model_dump_json()}) "
            + "is an organization member: "
            + f"{organization_member.model_dump_json()}. "
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
        backend_client.role_assignments.retrieve_by_user_id,
        active_user.id,
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
            f"User ({active_user.model_dump_json()}) "
            + "has platform role assignments: "
            + f"{RoleAssignmentListAdapter.dump_json(active_role_assignments_platform)}. "  # noqa: E501
            + "Skipping project member check",
        )
        return project_member

    # Check if user is project member
    if project_member:
        logger.debug(
            f"User ({active_user.model_dump_json()}) "
            + "is a project member: "
            + f"{project_member.model_dump_json()}. "
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
