import asyncio
import logging
import typing

import fastapi

import any_auth.deps.app_state as AppState
import any_auth.deps.permission
from any_auth.backend import BackendClient
from any_auth.deps.auth import depends_active_user
from any_auth.types.pagination import Page
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate
from any_auth.types.project_member import ProjectMember, ProjectMemberCreate
from any_auth.types.role import Permission, Role
from any_auth.types.user import UserInDB

logger = logging.getLogger(__name__)

router = fastapi.APIRouter()


@router.get("/organizations/{organization_id}/projects", tags=["Projects"])
async def api_list_projects(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve projects for"
    ),
    limit: int = fastapi.Query(default=20, ge=1, le=100),
    order: typing.Literal["asc", "desc"] = fastapi.Query(default="desc"),
    after: typing.Text = fastapi.Query(default=""),
    before: typing.Text = fastapi.Query(default=""),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_LIST, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Page[Project]:
    organization_id = organization_id.strip()
    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    page_projects = await asyncio.to_thread(
        backend_client.projects.list,
        organization_id=organization_id,
        limit=limit,
        order=order,
        after=after.strip() or None,
        before=before.strip() or None,
    )
    return Page[Project].model_validate(page_projects.model_dump())


@router.post("/organizations/{organization_id}/projects", tags=["Projects"])
async def api_create_project(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to create a project for"
    ),
    project_create: ProjectCreate = fastapi.Body(
        ..., description="The project to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_CREATE, from_="organization"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    organization_id = organization_id.strip()
    if not organization_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required",
        )

    project = await asyncio.to_thread(
        backend_client.projects.create,
        project_create,
        organization_id=organization_id,
        created_by=active_user.id,
    )
    return Project.model_validate(project.model_dump())


@router.get(
    "/organizations/{organization_id}/projects/{project_id}",
    tags=["Projects"],
)
async def api_retrieve_project(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve a project for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_GET, from_="project"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    organization_id = organization_id.strip()
    project_id = project_id.strip()

    if not project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required",
        )

    project = await asyncio.to_thread(backend_client.projects.retrieve, project_id)

    if not project:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return Project.model_validate(project.model_dump())


@router.post(
    "/organizations/{organization_id}/projects/{project_id}",
    tags=["Projects"],
)
async def api_update_project(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to update a project for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to update"
    ),
    project_update: ProjectUpdate = fastapi.Body(
        ..., description="The project to update"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_UPDATE, from_="project"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
) -> Project:
    organization_id = organization_id.strip()
    project_id = project_id.strip()

    if not project_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required",
        )

    project = await asyncio.to_thread(
        backend_client.projects.update,
        project_id,
        project_update,
    )
    return Project.model_validate(project.model_dump())


@router.delete(
    "/organizations/{organization_id}/projects/{project_id}",
    tags=["Projects"],
)
async def api_delete_project(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete a project for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_DELETE, from_="project"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.projects.set_disabled, project_id, disabled=True
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post(
    "/organizations/{organization_id}/projects/{project_id}/enable",
    tags=["Projects"],
)
async def api_enable_project(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to enable a project for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to enable"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_DISABLE, from_="project"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.projects.set_disabled, project_id, disabled=False
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.get(
    "/organizations/{organization_id}/projects/{project_id}/members",
    tags=["Projects"],
)
async def api_list_project_members(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve members for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve members for"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_MEMBER_LIST, from_="project"
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
    "/organizations/{organization_id}/projects/{project_id}/members",
    tags=["Projects"],
)
async def api_create_project_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to create a member for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to create a member for"
    ),
    member_create: ProjectMemberCreate = fastapi.Body(
        ..., description="The member to create"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_MEMBER_CREATE, from_="project"
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
    "/organizations/{organization_id}/projects/{project_id}/members/{member_id}",  # noqa: E501
    tags=["Projects"],
)
async def api_retrieve_project_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to retrieve a member for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to retrieve a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to retrieve"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_MEMBER_GET, from_="project"
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
    return ProjectMember.model_validate(project_member.model_dump())


@router.delete(
    "/organizations/{organization_id}/projects/{project_id}/members/{member_id}",  # noqa: E501
    tags=["Projects"],
)
async def api_delete_project_member(
    organization_id: typing.Text = fastapi.Path(
        ..., description="The ID of the organization to delete a member for"
    ),
    project_id: typing.Text = fastapi.Path(
        ..., description="The ID of the project to delete a member for"
    ),
    member_id: typing.Text = fastapi.Path(
        ..., description="The ID of the member to delete"
    ),
    active_user: UserInDB = fastapi.Depends(depends_active_user),
    user_roles: typing.Tuple[UserInDB, typing.List[Role]] = fastapi.Depends(
        any_auth.deps.permission.depends_permissions(
            Permission.PROJECT_MEMBER_DELETE, from_="project"
        )
    ),
    backend_client: BackendClient = fastapi.Depends(AppState.depends_backend_client),
):
    await asyncio.to_thread(
        backend_client.project_members.delete,
        member_id=member_id,
    )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
