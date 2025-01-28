import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.utils.to_ as TO
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import PLATFORM_ID
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


async def verify_permission(
    required_permissions: list[Permission],
    *,
    active_user: UserInDB,
    resource_id: str,
    backend_client: BackendClient,
) -> tuple[UserInDB, list[Role]]:
    """
    Checks whether `active_user` has all the `required_permissions`
    on the given `resource_id`.
    """

    # Retrieve all roles the user has on that resource
    user_roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_user_id,
        user_id=active_user.id,
        resource_id=resource_id,
    )

    # Consolidate permissions from all roles
    user_perms = set()
    for role in user_roles:
        user_perms.update(role.permissions)

    # Check if user is missing anything
    missing = set(required_permissions) - user_perms
    if missing:
        _missing_str = ", ".join(f"'{str(TO.to_enum_value(perm))}'" for perm in missing)
        _needed_str = ", ".join(
            f"'{str(TO.to_enum_value(perm))}'" for perm in required_permissions
        )
        logger.warning(
            f"User '{active_user.id}' lacks permissions: {_missing_str}. "
            f"Needed: {_needed_str}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return (active_user, user_roles)


def depends_resource_id_from_path_organization(
    organization_id: str = fastapi.Path(...),
) -> str:
    org = organization_id.strip()
    if not org:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization path parameter is required.",
        )
    return org


def depends_resource_id_from_path_project(project_id: str = fastapi.Path(...)) -> str:
    project_id = project_id.strip()
    if not project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Project path parameter is required.",
        )
    return project_id


def depends_resource_id_from_query(
    organization_id: str = fastapi.Query(default=""),
    project_id: str = fastapi.Query(default=""),
) -> str:
    resource_id = organization_id.strip() or project_id.strip()
    if not resource_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Resource ID is required.",
        )
    return resource_id


def depends_permissions(
    *required_permissions: Permission,
    resource_id_source: typing.Literal[
        "organization", "project", "query", "platform"
    ] = "organization",
) -> typing.Callable[..., typing.Coroutine[None, None, tuple[UserInDB, list[Role]]]]:
    """
    Returns a FastAPI dependency that yields (user, roles),
    ensuring the given `required_permissions` are all met
    for the resource ID extracted from the request (org or project).
    """

    # Decide how we want to extract the resource_id:
    if resource_id_source == "organization":
        resource_id_dep = depends_resource_id_from_path_organization
    elif resource_id_source == "project":
        resource_id_dep = depends_resource_id_from_path_project
    elif resource_id_source == "platform":
        resource_id_dep = lambda: PLATFORM_ID  # noqa: E731
    else:
        # fallback to reading from query param
        resource_id_dep = depends_resource_id_from_query

    # The actual dependency function
    async def _dependency(
        active_user: UserInDB = fastapi.Depends(depends_active_user),
        resource_id: str = fastapi.Depends(resource_id_dep),
        backend_client: BackendClient = fastapi.Depends(
            AppState.depends_backend_client
        ),
    ) -> tuple[UserInDB, list[Role]]:
        return await verify_permission(
            list(required_permissions),
            active_user=active_user,
            resource_id=resource_id,
            backend_client=backend_client,
        )

    return _dependency
