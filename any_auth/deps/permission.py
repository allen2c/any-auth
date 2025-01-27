# any_auth/deps/permission.py (Create a new file for permission dependencies)

import asyncio
import logging
from typing import List, Set

import fastapi

import any_auth.deps.app_state as AppState
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.role import Permission
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


async def verify_permission(
    required_permissions: List[Permission],
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> UserInDB:
    """
    Dependency to verify if the active user has the required permissions.
    """
    user_roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_user_id,
        user_id=active_user.id,
        resource_id="<YOUR_RESOURCE_ID_CONTEXT>",
    )

    user_permissions: Set[Permission] = set()
    for role in user_roles:
        user_permissions.update(role.permissions)

    missing_permissions = set(required_permissions) - user_permissions

    if missing_permissions:
        _str_missing_permissions = ", ".join(missing_permissions)
        _str_required_permissions = ", ".join(required_permissions)
        logger.warning(
            f"User {active_user.id} lacks permissions: {_str_missing_permissions}. "
            + f"Required: {_str_required_permissions}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return active_user


# Helper function for convenience (optional)
def permission_dependency(*required_permissions: Permission):
    """
    Returns a dependency that verifies the required permissions.
    """

    async def _permission_check(
        user: UserInDB = fastapi.Depends(
            lambda: verify_permission(list(required_permissions))
        ),
    ):
        return user

    return _permission_check
