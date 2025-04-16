# any_auth/api/proj_aks_ras.py
# use RBAC
import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.deps.role_assignment import raise_if_role_assignment_denied
from any_auth.types.pagination import Page
from any_auth.types.role import Permission, Role
from any_auth.types.role_assignment import (
    APIKeyRoleAssignmentCreate,
    RoleAssignment,
    RoleAssignmentCreate,
)
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get(
    "/projects/{project_id}/api-keys/{api_key_id}/role-assignments",  # noqa: E501
    tags=["Projects"],
)
async def api_retrieve_project_api_key_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve an API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.IAM_GET_POLICY,
        )
    ),
) -> Page[RoleAssignment]:
    target_project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )
    if not target_project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    if target_project_api_key.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=target_project_api_key.id,
        resource_id=project_id,
    )
    return Page[RoleAssignment].model_validate(
        {
            "object": "list",
            "data": role_assignments,
            "first_id": role_assignments[0].id if role_assignments else None,
            "last_id": role_assignments[-1].id if role_assignments else None,
            "has_more": False,
        }
    )


@router.post(
    "/projects/{project_id}/api-keys/{api_key_id}/role-assignments",
    tags=["Projects"],
)
async def api_create_project_api_key_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create an API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to create a role assignment for"
    ),
    api_key_role_assignment_create: APIKeyRoleAssignmentCreate = fastapi.Body(
        ..., description="The role assignment to create"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.IAM_SET_POLICY,
        )
    ),
) -> RoleAssignment:
    target_project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )
    if not target_project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if target_project_api_key.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    role_assignment_create = await asyncio.to_thread(
        api_key_role_assignment_create.to_role_assignment_create,
        backend_client=backend_client,
        target_id=target_project_api_key.id,
        resource_id=project_id,
    )

    # Check if user has permission to assign the target role
    await raise_if_role_assignment_denied(
        role_assignment_create,
        active_user_roles,
        backend_client=backend_client,
    )

    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.create,
        role_assignment_create,
    )

    return role_assignment


@router.put(
    "/projects/{project_id}/api-keys/{api_key_id}/role-assignments",
    tags=["Projects"],
)
async def api_update_project_api_key_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to update role assignments in"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to update role assignments for"
    ),
    api_key_role_assignment_creates: typing.List[
        APIKeyRoleAssignmentCreate
    ] = fastapi.Body(
        ..., description="Replace the existing role assignments with the new ones"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.IAM_SET_POLICY,
        )
    ),
) -> typing.List[RoleAssignment]:
    target_project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )
    if not target_project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if target_project_api_key.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    role_assignment_creates = [
        await asyncio.to_thread(
            api_key_role_assignment_create.to_role_assignment_create,
            backend_client=backend_client,
            target_id=target_project_api_key.id,
            resource_id=project_id,
        )
        for api_key_role_assignment_create in api_key_role_assignment_creates
    ]

    # Check if user has permission to assign the target role
    for role_assignment_create in role_assignment_creates:
        await raise_if_role_assignment_denied(
            role_assignment_create,
            active_user_roles,
            backend_client=backend_client,
        )

    output_role_assignments_map: typing.Dict[typing.Text, RoleAssignment | None] = {
        role_assignment_create.role_id: None
        for role_assignment_create in role_assignment_creates
    }
    existing_role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=target_project_api_key.id,
        resource_id=project_id,
    )

    # Role assignments to delete
    role_assignments_to_delete = [
        role_assignment
        for role_assignment in existing_role_assignments
        if role_assignment.role_id
        not in (
            role_assignment_create.role_id
            for role_assignment_create in role_assignment_creates
        )
    ]

    # Role assignments to create
    role_assignments_to_create: typing.List["RoleAssignmentCreate"] = []
    for role_assignment_create in role_assignment_creates:
        for existing_role_assignment in existing_role_assignments:
            if role_assignment_create.role_id == existing_role_assignment.role_id:
                output_role_assignments_map[role_assignment_create.role_id] = (
                    existing_role_assignment
                )
                break
        else:
            role_assignments_to_create.append(role_assignment_create)

    # Create new role assignments
    if len(role_assignments_to_create) > 0:
        logger.debug(
            f"Creating {len(role_assignments_to_create)} role assignments for {api_key_id} in {project_id}"  # noqa: E501
        )
        for role_assignment_create in role_assignments_to_create:
            role_assignment = await asyncio.to_thread(
                backend_client.role_assignments.create,
                role_assignment_create,
            )
            output_role_assignments_map[role_assignment_create.role_id] = (
                role_assignment
            )

    # Delete existing role assignments
    if len(role_assignments_to_delete) > 0:
        logger.debug(
            f"Deleting {len(role_assignments_to_delete)} role assignments for {api_key_id} in {project_id}"  # noqa: E501
        )
        for role_assignment in role_assignments_to_delete:
            await asyncio.to_thread(
                backend_client.role_assignments.delete,
                role_assignment.id,
            )

    return [ra for ra in output_role_assignments_map.values() if ra is not None]


@router.delete(
    "/projects/{project_id}/api-keys/{api_key_id}/role-assignments/{role_assignment_id}",  # noqa: E501
    tags=["Projects"],
)
async def api_delete_project_api_key_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create a API key for"
    ),
    api_key_id: typing.Text = fastapi.Path(
        ..., description="The ID of the API key to create a role assignment for"
    ),
    role_assignment_id: typing.Text = fastapi.Path(
        ..., description="The ID of the role assignment to delete"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.IAM_SET_POLICY,
        )
    ),
):
    role_assignment = await asyncio.to_thread(
        backend_client.role_assignments.retrieve,
        role_assignment_id,
    )
    if not role_assignment:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    if role_assignment.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    target_project_api_key = await asyncio.to_thread(
        backend_client.api_keys.retrieve,
        api_key_id=api_key_id,
    )
    if not target_project_api_key:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if target_project_api_key.resource_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if role_assignment.target_id != target_project_api_key.id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    await asyncio.to_thread(
        backend_client.role_assignments.delete,
        role_assignment_id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
