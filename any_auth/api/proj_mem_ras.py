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
from any_auth.types.role_assignment import MemberRoleAssignmentCreate, RoleAssignment
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get(
    "/projects/{project_id}/members/{member_id}/role-assignments",  # noqa: E501
    tags=["Projects"],
)
async def api_retrieve_project_member_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.IAM_GET_POLICY,
        )
    ),
) -> Page[RoleAssignment]:
    target_project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id=member_id,
    )
    if not target_project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    if target_project_member.project_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_member_id,
        member_id=member_id,
        type="project",
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
    "/projects/{project_id}/members/{member_id}/role-assignments",  # noqa: E501
    tags=["Projects"],
)
async def api_create_project_member_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to create a role assignment for"
    ),
    member_role_assignment_create: MemberRoleAssignmentCreate = fastapi.Body(
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
    target_project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id,
    )
    if not target_project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if target_project_member.project_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    role_assignment_create = await asyncio.to_thread(
        member_role_assignment_create.to_role_assignment_create,
        backend_client=backend_client,
        user_id=target_project_member.user_id,
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


@router.delete(
    "/projects/{project_id}/members/{member_id}/role-assignments/{role_assignment_id}",  # noqa: E501
    tags=["Projects"],
)
async def api_delete_project_member_role_assignment(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to create a role assignment for"
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

    target_project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id,
    )
    if not target_project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if target_project_member.project_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if role_assignment.user_id != target_project_member.user_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    await asyncio.to_thread(
        backend_client.role_assignments.delete,
        role_assignment_id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
