import logging
import typing

import fastapi

from any_auth.backend import BackendClient
from any_auth.types.role import NA_ROLE, Role, RoleUpdate
from any_auth.types.role_assignment import RoleAssignmentCreate
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)


async def raise_if_role_assignment_denied(
    role_assignment_create: RoleAssignmentCreate,
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]],
    *,
    backend_client: BackendClient,
) -> typing.Literal[True]:
    target_role = await raise_if_role_not_found(
        role_assignment_create, active_user_roles, backend_client=backend_client
    )
    target_user = await raise_if_user_not_found(
        role_assignment_create, active_user_roles, backend_client=backend_client
    )

    if await allow_na_role(
        role_assignment_create,
        active_user_roles,
        backend_client=backend_client,
        target_user=target_user,
        target_role=target_role,
    ):
        logger.info(
            f"Passed NA role check for user ({target_user.model_dump_json()}) "
            + f"with query body: ({role_assignment_create.model_dump_json()})"
        )
        return True

    await raise_if_assigning_role_not_in_user_child_roles(
        role_assignment_create, active_user_roles, backend_client=backend_client
    )

    return True


async def raise_if_role_not_found(
    role_assignment_create: RoleAssignmentCreate,
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]],
    *,
    backend_client: BackendClient,
) -> Role:
    role = backend_client.roles.retrieve(id=role_assignment_create.role_id)
    if role is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    return role


async def raise_if_user_not_found(
    role_assignment_create: RoleAssignmentCreate,
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]],
    *,
    backend_client: BackendClient,
) -> UserInDB:
    user = backend_client.users.retrieve(id=role_assignment_create.user_id)
    if user is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def allow_na_role(
    role_assignment_create: RoleAssignmentCreate,
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]],
    *,
    backend_client: BackendClient,
    target_user: UserInDB,
    target_role: Role | None = None,
) -> bool:
    if target_role is None:
        target_role = backend_client.roles.retrieve(role_assignment_create.role_id)

    if target_role is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    role_na = backend_client.roles.retrieve_by_id_or_name(NA_ROLE.name)
    if role_na is None:
        logger.warning(
            f"Role {NA_ROLE.name} not found, but user is trying to assign it"
        )
        return False

    if target_role.name != NA_ROLE.name:
        return False  # Not the NA role

    if (
        target_role.name == NA_ROLE.name
        and role_assignment_create.role_id == role_na.id
    ):
        if len(target_role.permissions) == 0:
            logger.info(
                f"Active user ({active_user_roles[0].model_dump_json()}) "
                + f"is trying to assign NA role ({role_na.model_dump_json()}) "
                + f"to user ({target_user.model_dump_json()}) "
                + f"with query body: ({role_assignment_create.model_dump_json()})"
            )
            return True
        else:
            logger.error(
                f"Denied NA role assignment for user ({target_user.model_dump_json()}) "
                + f"with query body: ({role_assignment_create.model_dump_json()}). "
                + "NA role should not have any permissions: "
                + f"{target_role.model_dump_json()}. "
            )
            logger.error(
                "NA role with permissions will cause a security risk. Hard code to "
                + "delete the permissions from the NA role in background."
            )
            backend_client.roles.update(
                id=role_na.id,
                role_update=RoleUpdate(permissions=[]),
            )
            return False

    return False  # Not the NA role


async def raise_if_assigning_role_not_in_user_child_roles(
    role_assignment_create: RoleAssignmentCreate,
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]],
    *,
    backend_client: BackendClient,
) -> typing.Literal[True]:
    roles_map: typing.Dict[typing.Text, Role] = {
        role.id: role for role in active_user_roles[1]
    }

    # Get all child roles for the user
    for role in tuple(roles_map.values()):
        roles_map.update(
            {
                role.id: role
                for role in backend_client.roles.retrieve_all_child_roles(role.id)
            }
        )

    # Check if the role is in the user's child roles
    if role_assignment_create.role_id not in roles_map:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Role not found in user's child roles",
        )

    return True
