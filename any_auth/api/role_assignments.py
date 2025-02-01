import asyncio
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.permission
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import RoleAssignment, RoleAssignmentCreate
from any_auth.types.user import UserInDB

router = fastapi.APIRouter()


async def raise_if_assigning_role_not_in_user_child_roles(
    role_assignment_create: RoleAssignmentCreate,
    user_roles: typing.Tuple[UserInDB, typing.List[Role]],
    *,
    backend_client: BackendClient,
) -> typing.Literal[True]:
    roles_map: typing.Dict[typing.Text, Role] = {
        role.id: role for role in user_roles[1]
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
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Role not found in user's child roles",
        )

    return True


@router.post("/role-assignments", tags=["Role Assignments"])
async def api_create_role_assignment(
    role_assignment_create: RoleAssignmentCreate = fastapi.Body(
        ..., description="The role assignment to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_SET_POLICY,
            resource_id_source="platform",
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> RoleAssignment:

    # Check if user has permission to assign the target role
    await raise_if_assigning_role_not_in_user_child_roles(
        role_assignment_create, user_roles, backend_client=backend_client
    )

    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.create,
        role_assignment_create,
    )
    return RoleAssignment.model_validate(role_assignment.model_dump())


@router.get("/role-assignments/{role_assignment_id}", tags=["Role Assignments"])
async def api_retrieve_role_assignment(
    role_assignment_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role assignment to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_GET_POLICY,
            resource_id_source="platform",
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> RoleAssignment:
    role_assignment_id = role_assignment_id.strip()

    if not role_assignment_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Role Assignment ID is required",
        )

    role_assignment_in_db = await asyncio.to_thread(
        backend_client.role_assignments.retrieve, role_assignment_id
    )

    if not role_assignment_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role Assignment not found",
        )

    return RoleAssignment.model_validate(role_assignment_in_db.model_dump())


@router.delete("/role-assignments/{role_assignment_id}", tags=["Role Assignments"])
async def api_delete_role_assignment(
    role_assignment_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role assignment to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.IAM_SET_POLICY,
            resource_id_source="platform",
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    role_assignment_id = role_assignment_id.strip()

    if not role_assignment_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Role Assignment ID is required",
        )

    role_assignment_in_db = await asyncio.to_thread(
        backend_client.role_assignments.retrieve, role_assignment_id
    )

    if not role_assignment_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role Assignment not found",
        )

    await asyncio.to_thread(backend_client.role_assignments.delete, role_assignment_id)

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
