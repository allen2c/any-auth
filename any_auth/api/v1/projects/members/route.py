# any_auth/api/v1/projects/members/route.py
# use RBAC
import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.auth
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate
from any_auth.types.role import Permission, Role
from any_auth.types.user import User, UserInDB

from .role_assignments.route import router as rs_router

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get(
    "/projects/{project_id}/members",
    tags=["Projects"],
)
async def api_list_project_members(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve members for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_LIST,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[ProjectMember]:
    project_members = await asyncio.to_thread(
        backend_client.project_members.retrieve_by_project_id,
        project_id=project_id,
    )
    return Page[ProjectMember].model_validate(
        {
            "object": "list",
            "data": project_members,
            "first_id": project_members[0].id if project_members else None,
            "last_id": project_members[-1].id if project_members else None,
            "has_more": False,
        }
    )


@router.post(
    "/projects/{project_id}/members",
    tags=["Projects"],
)
async def api_create_project_member(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create a member for"
    ),
    member_create: ProjectMemberCreate = fastapi.Body(
        ..., description="The member to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_CREATE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> ProjectMember:
    project_member = await asyncio.to_thread(
        backend_client.project_members.create,
        member_create,
        project_id=project_id,
    )
    return ProjectMember.model_validate(project_member.model_dump())


@router.get(
    "/projects/{project_id}/members/{member_id}",
    tags=["Projects"],
)
async def api_retrieve_project_member(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> ProjectMember:
    project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id=member_id,
    )
    if not project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )
    if project_member.project_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )
    return ProjectMember.model_validate(project_member.model_dump())


@router.delete(
    "/projects/{project_id}/members/{member_id}",
    tags=["Projects"],
)
async def api_delete_project_member(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to delete a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_DELETE,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    target_project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id=member_id,
    )

    # Raise an error if the project member is not found
    if not target_project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    # Raise an error if the project member is not in the project
    if target_project_member.project_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    # Delete all role assignments for the project member
    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_target_id,
        target_id=target_project_member.user_id,
        resource_id=project_id,
    )
    for role_assignment in role_assignments:
        await asyncio.to_thread(
            backend_client.role_assignments.delete,
            role_assignment.id,
        )

    # Delete the project member
    await asyncio.to_thread(
        backend_client.project_members.delete,
        member_id=member_id,
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get(
    "/projects/{project_id}/members/{member_id}/user",
    tags=["Projects"],
)
async def api_retrieve_project_member_user(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> User:
    project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id=member_id,
    )

    if not project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    user_in_db = await asyncio.to_thread(
        backend_client.users.retrieve,
        project_member.user_id,
    )

    if not user_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return User.model_validate(user_in_db.model_dump())


@router.get(
    "/projects/{project_id}/members/{member_id}/roles",
    tags=["Projects"],
)
async def api_retrieve_project_member_roles(
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    active_user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.auth.depends_permissions_for_project(
            Permission.PROJECT_MEMBER_GET,
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Role]:
    project_member = await asyncio.to_thread(
        backend_client.project_members.retrieve,
        member_id=member_id,
    )

    if not project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    role_assignments = await asyncio.to_thread(
        backend_client.role_assignments.retrieve_by_member_id,
        member_id=project_member.id,
        type="project",
        resource_id=project_id,
    )

    if len(role_assignments) == 0:
        return Page[Role].model_validate(
            {
                "object": "list",
                "data": [],
                "first_id": None,
                "last_id": None,
                "has_more": False,
            }
        )

    roles = await asyncio.to_thread(
        backend_client.roles.retrieve_by_ids,
        [assignment.role_id for assignment in role_assignments],
    )
    return Page[Role].model_validate(
        {
            "object": "list",
            "data": roles,
            "first_id": roles[0].id if roles else None,
            "last_id": roles[-1].id if roles else None,
            "has_more": False,
        }
    )


router.include_router(rs_router)
