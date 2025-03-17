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
from any_auth.types.user import UserInDB

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
    if not target_project_member:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )
    if target_project_member.project_id != project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    await asyncio.to_thread(
        backend_client.project_members.delete,
        member_id=member_id,
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
